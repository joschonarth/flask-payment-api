from flask import Flask, jsonify
from repository.database import db
from db_models.payment import Payment

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'secret_key_payment_project'

db.init_app(app)

@app.route('/payments/pix', methods=['POST'])
def create_payment_pix():
    return jsonify({"message": "The payment has benn created"})

@app.route('/payments/pix/confirmation', methods=['POST'])
def pix_confirmation():
    return jsonify({"message": "The payment has benn confirmed"})

@app.route('/payments/pix/<int:payment_id>', methods=['GET'])
def payment_pix_page(payment_id):
    return 'Pix Payment'

if __name__ == '__main__':
    app.run(debug=True)