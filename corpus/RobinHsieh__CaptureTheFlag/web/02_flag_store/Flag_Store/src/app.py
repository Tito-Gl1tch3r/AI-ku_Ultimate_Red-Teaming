from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask import render_template_string
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///agdnaljtt12jlkjal12312bdhbfjbdfhasbfjasd.db'
db = SQLAlchemy(app)
app.secret_key = "thisisfake"

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True)
    money = db.Column(db.Float)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    price = db.Column(db.Float)
    description = db.Column(db.String(255))

# 初始化 database
with app.app_context():
    db.create_all()
    # 添加商品數據
    products_data = [
        {"name": "Flag", "price": 10000000, "description": "ADL{thisisfake}"},
        {"name": "hint 1", "price": 10, "description": "TA's email: happyyung881115@gmail.com"},
        {"name": "hint 2", "price": 4999, "description": "Do you know SSTI !!!!"},
    ]
    for product_data in products_data:
        product = Product(**product_data)
        db.session.add(product)

    # 添加 users 數據
    users_data = [
        {"username": 'guest', "money": 100},
        {"username": 'admin', "money": 5000},
        {"username": 'jack', "money": 48763},
        {"username": '1mv32yv32y21ch', "money": 100000000000},
    ]
    for user_data in users_data:
        user = User(**user_data)
        db.session.add(user)

    db.session.commit()

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/ItemList")
def Items():
    msg = session.pop('msg', None)
    user = session.get('user')
    user_obj = User.query.filter_by(username=user).first()
    money = user_obj.money if user_obj else 100
    products = Product.query.all()
    return render_template("ItemList.html", products=products, money=money, msg=msg)

@app.route('/welcome')
def welcome():
    refresh_money()
    try:
        template = '''
                <div class="center-content error">
                    <h3>%s</h3>
                    <a href="/ItemList">Store</a>
                </div>
            '''%(session['msg'])
        return render_template_string(template)
    except:
        return "Error !!!!!"

@app.route("/whoareyou", methods=['GET', 'POST'])
def identify():
    if request.method == 'POST':
        user_input = request.form.get('user_input')
        if len(user_input) >= 20:
            return 'Your input is too long'

        blacklist = ['config', '_', 'os', 'init', '.', 'builtin', 'mro', 'cat', 'id',
                    'self', 'context', 'function', 'local', 'request', 'session', 'base', 'url_for', 'globals']
        for b in blacklist:
            if b in user_input:
                user_input = user_input.replace(b, '')

        try:
            msg = "Hello {user_input}".format(user_input=eval(user_input))
        except:
            msg = "Hello {user_input}".format(user_input=user_input)

        user = User.query.filter_by(username=user_input).first()
        if not user:
            msg = msg+",         This username isn't exist, so you are guest"
            session['msg'] = msg
            session['user'] = 'guest'
        else:
            if user.username == '1mv32yv32y21ch':
                return 'Access denied. You are a VIP. Please use a more secure method to log in.'
            session['msg'] = msg
            session['user'] = user.username


        return redirect(url_for("welcome"))

    return render_template("whoareyou.html")

@app.route('/purchase', methods=['POST'])
def purchase():
    data = request.get_json()
    user = session.get('user')

    if user is None:
        return jsonify({'message': 'User not authenticated'})

    if 'productId' in data:
        product_id = int(data['productId'])
        user_obj = User.query.filter_by(username=user).first()
        money = user_obj.money if user_obj else 100
        product = Product.query.get(product_id)

        if not product:
            return jsonify({'message': 'Product not found'})
        if not user_obj:
                return jsonify({'message': 'User not found'})

        if money < product.price:
            return jsonify({'message': 'No enough money', 'money': money})
        else:
            user_obj.money -= product.price
            db.session.commit()

            msg = 'Purchase successful\n' + product.description

            return jsonify({'message': msg, 'money': user_obj.money})

def refresh_money():
    user_obj = User.query.filter_by(username='guest').first()
    user_obj.money = 100
    user_obj = User.query.filter_by(username='admin').first()
    user_obj.money = 5000
    user_obj = User.query.filter_by(username='jack').first()
    user_obj.money = 48763
    user_obj = User.query.filter_by(username='1mv32yv32y21ch').first()
    user_obj.money = 100000000000
    db.session.commit()

if __name__ == '__main__':
    app.run('0.0.0.0', 80)
