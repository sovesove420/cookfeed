from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cookfeed.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
db = SQLAlchemy(app)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class ShoppingItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(200), nullable=False)
    checked = db.Column(db.Boolean, default=False)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    ingredients = db.Column(db.String(500), nullable=False)
    emoji = db.Column(db.String(10), default='🍽️')
    image = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    method = db.Column(db.Text, nullable=True)

with app.app_context():
    db.create_all()

@app.route('/')
def home():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('index.html', posts=posts)

@app.route('/shopping')
def shopping():
    return render_template('shopping.html')

@app.route('/new')
def new_post():
    return render_template('new_post.html')

@app.route('/api/posts', methods=['POST'])
def create_post():
    username = request.form.get('username')
    title = request.form.get('title')
    description = request.form.get('description')
    ingredients = request.form.get('ingredients')
    emoji = request.form.get('emoji')
    method = request.form.get('method')

    image_filename = None
    if 'image' in request.files:
        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_filename = filename

    post = Post(
        username=username,
        title=title,
        description=description,
        ingredients=ingredients,
        emoji=emoji,
        image=image_filename,
        method=method

    )
    db.session.add(post)
    db.session.commit()
    return jsonify({'message': 'created', 'id': post.id})

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