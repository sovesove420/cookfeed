from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from sqlalchemy import text
from datetime import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash
import cloudinary
import cloudinary.uploader

cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME', ''),
    api_key=os.environ.get('CLOUDINARY_API_KEY', ''),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET', ''),
)

app = Flask(__name__)
uri = os.environ.get('DATABASE_URL', 'sqlite:///cookfeed.db')
if uri.startswith('postgres://'):
    uri = uri.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
db = SQLAlchemy(app)
login_manager = LoginManager(app)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    profile_pic = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class ShoppingItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(200), nullable=False)
    checked = db.Column(db.Boolean, default=False)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    username = db.Column(db.String(50), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    ingredients = db.Column(db.String(500), nullable=False)
    emoji = db.Column(db.String(10), default='🍽️')
    image = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    method = db.Column(db.Text, nullable=True)
    reactions = db.Column(db.Integer, default=0)

    @property
    def display_username(self):
        return self.author.username if self.author else (self.username or 'Anonymous')

    author = db.relationship('User', backref=db.backref('posts', lazy=True))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to post a recipe.'

with app.app_context():
    db.create_all()
    try:
        db.session.execute(text("ALTER TABLE post ADD COLUMN reactions INTEGER DEFAULT 0"))
        db.session.commit()
    except Exception:
        db.session.rollback()
    try:
        db.session.execute(text("ALTER TABLE post ADD COLUMN user_id INTEGER REFERENCES user(id)"))
        db.session.commit()
    except Exception:
        db.session.rollback()

@app.route('/')
def home():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('index.html', posts=posts)

@app.route('/shopping')
def shopping():
    return render_template('shopping.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        if not username or not email or not password:
            flash('Please fill in all fields.', 'error')
            return redirect(url_for('register'))
        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'error')
            return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return redirect(url_for('register'))
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('home'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next', url_for('home'))
            return redirect(next_page)
        flash('Invalid username or password.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/profile')
@login_required
def profile():
    posts = Post.query.filter_by(user_id=current_user.id).order_by(Post.created_at.desc()).all()
    return render_template('profile.html', user=current_user, posts=posts)

@app.route('/new')
@login_required
def new_post():
    return render_template('new_post.html')

@app.route('/api/posts', methods=['POST'])
@login_required
def create_post():
    title = request.form.get('title')
    description = request.form.get('description')
    ingredients = request.form.get('ingredients')
    emoji = request.form.get('emoji')
    method = request.form.get('method')

    image_url = None
    if 'image' in request.files:
        file = request.files['image']
        if file and file.filename and allowed_file(file.filename):
            try:
                result = cloudinary.uploader.upload(file, use_filename=True)
                image_url = result.get('secure_url') or result.get('url')
            except Exception:
                pass

    post = Post(
        user_id=current_user.id,
        username=current_user.username,
        title=title,
        description=description,
        ingredients=ingredients,
        emoji=emoji,
        image=image_url,
        method=method

    )
    db.session.add(post)
    db.session.commit()
    return jsonify({'message': 'created', 'id': post.id})

@app.route('/api/posts/<int:post_id>/react', methods=['POST'])
def react_post(post_id):
    post = Post.query.get_or_404(post_id)
    post.reactions = (post.reactions or 0) + 1
    db.session.commit()
    return jsonify({'reactions': post.reactions})

@app.route('/api/items', methods=['GET'])
def get_items():
    items = ShoppingItem.query.all()
    return jsonify([{'id': item.id, 'text': item.text, 'checked': item.checked} for item in items])

@app.route('/api/items', methods=['POST'])
def add_item():
    data = request.json
    new_item = ShoppingItem(text=data['text'])
    db.session.add(new_item)
    db.session.commit()
    return jsonify({'id': new_item.id, 'text': new_item.text, 'checked': new_item.checked})

@app.route('/api/items/<int:item_id>', methods=['PUT'])
def toggle_item(item_id):
    item = ShoppingItem.query.get(item_id)
    item.checked = not item.checked
    db.session.commit()
    return jsonify({'id': item.id, 'text': item.text, 'checked': item.checked})

@app.route('/api/items/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    item = ShoppingItem.query.get(item_id)
    db.session.delete(item)
    db.session.commit()
    return jsonify({'message': 'deleted'})

  

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)