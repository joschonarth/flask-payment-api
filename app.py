from flask import Flask, jsonify, request, send_file, render_template
from repository.database import db
from db_models.payment import Payment
from datetime import datetime, timedelta
from payments.pix import Pix
from flask_socketio import SocketIO
from flask_apscheduler import APScheduler

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'secret_key_payment_project'

db.init_app(app)
socketio = SocketIO(app)

class Config:
    SCHEDULER_API_ENABLED = True

app.config.from_object(Config)
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

@app.route('/payments/pix', methods=['POST'])
def create_payment_pix():
    data = request.get_json()

    if 'value' not in data:
        return jsonify({"message": "Invalid value"}), 400
    
    expiration_date = datetime.now() + timedelta(minutes=30)

    new_payment = Payment(value=data['value'], expiration_date=expiration_date)

    pix_obj = Pix()
    data_payment_pix = pix_obj.create_payment()
    new_payment.bank_payment_id = data_payment_pix["bank_payment_id"]
    new_payment.qr_code = data_payment_pix["qr_code_path"]

    db.session.add(new_payment)
    db.session.commit()
    
    return jsonify({"message": "The payment has benn created", 
                    "payment": new_payment.to_dict()})

@app.route('/payments/pix/qr_code/<file_name>', methods=['GET'])
def get_image(file_name):
    return send_file(f"static/img/{file_name}.png", mimetype='image/png')

@app.route('/payments/pix/confirmation', methods=['POST'])
def pix_confirmation():
    data = request.get_json()

    if "bank_payment_id" not in data and "value" not in data:
        return jsonify({"message": "Invalid payment data"}), 400

    payment = Payment.query.filter_by(bank_payment_id=data.get("bank_payment_id")).first()

    if not payment or payment.paid:
        return jsonify({"message": "Payment not found"}), 404
    
    if data.get("value") != payment.value:
        return jsonify({"message": "Invalid payment data"}), 400
    
    payment.paid = True
    db.session.commit()
    socketio.emit(f'payment-confirmed-{payment.id}')

    return jsonify({"message": "The payment has benn confirmed"})

@app.route('/payments/pix/<int:payment_id>', methods=['GET'])
def payment_pix_page(payment_id):
    payment = Payment.query.get(payment_id)

    if not payment:
        return render_template('404.html')

    if payment.paid:
        return render_template(
            'confirmed_payment.html',
            payment_id=payment.id, 
            value=payment.value
        )

    return render_template(
        'payment.html', 
        payment_id=payment.id, 
        value=payment.value, 
        host="http://127.0.0.1:5000", 
        qr_code=payment.qr_code
    )

@app.route('/payments/expired/<int:payment_id>', methods=['GET'])
def payment_expired_page(payment_id):
    payment = Payment.query.get(payment_id)

    if not payment:
        return render_template('404.html')

    return render_template(
        'expired_payment.html',
        payment_id=payment.id,
        value=payment.value,
        expiration_date=payment.expiration_date
    )

def check_expired_payments():
    with app.app_context():
        expired_payments = Payment.query.filter(
            Payment.expiration_date < datetime.now(),
            Payment.paid == False
        ).all()

        for payment in expired_payments:
            socketio.emit(
                f'payment-expired-{payment.id}',
                {"message": "Payment expired", "payment_id": payment.id}
            )

scheduler.add_job(
    id='check_expired_payments',
    func=check_expired_payments,
    trigger='interval',
    minutes=1
)

@socketio.on('connect')
def handle_connect():
    print("Client connected to the server")

@socketio.on('disconnect')
def handle_disconnect():
    print("Client has disconnected from the server")

if __name__ == '__main__':
    socketio.run(app, debug=True)