from flask import Flask, request, render_template
from urllib.parse import parse_qs
import braintree
import apini
import elks
import os
import re

app = Flask(__name__)
baseurl = 'https://apini.theusr.org/pay/%s'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/incomingsms', methods=['POST'])
def incomingsms():
    rawmessage = request.form['message'].strip()
    rawmessage = rawmessage.split()
    rawmessage = list(map(lambda x: x.strip(), rawmessage))
    sender = request.form['from']
    if len(rawmessage) < 2:
        return ''
    if re.match("\+[0-9]*", rawmessage[0]):
        recipient = rawmessage[0]
        amount = rawmessage[2]
    else:
        recipient = sender
        amount = rawmessage[1]
    amount = int(amount)
    if amount > 15000:
        return 'Wow. That\'s way too much money for a little bee. Nope.\n'
    url = apini.insert_transaction(amount, sender, recipient)
    if recipient == sender:
        return "Hey there, the payment of SEK %s may now be payed at\n%s" % (
                amount, baseurl % url)
    else:
        elks.send_url(baseurl % url, amount, sender, recipient)
    return ''

@app.route('/pay', methods=['POST'])
def post_handler():
    uri = request.form['paytoken']
    if apini.is_payed(uri):
        return render_template('resultpage.html', paid=True, good=False)
    else:
        result = braintree.Transaction.sale({
            "amount": apini.get_amount(uri),
            "payment_method_nonce": request.form['payment_method_nonce'],
            "options": {
                "submit_for_settlement": True
            }
        })
        if result.is_success:
            apini.mark_as_payed(uri)
            parts = apini.get_transaction_parts(uri)
            sender = parts[0]
            recipient = parts[1]
            amount = parts[2]
            elks.has_payed(recipient, sender, amount)
            return render_template('resultpage.html', good=True, paid=False)
        else:
            return render_template('resultpage.html', good=False, paid=False, uri=uri)

@app.route('/pay/<payid>')
def pay(payid):
    if apini.is_payed(payid):
        return render_template('resultpage.html', paid=True, good=False)
    braintree.Configuration.configure(braintree.Environment.Sandbox,
        merchant_id=os.environ['BT_MERCHANT_ID'],
        public_key=os.environ['BT_PUBLIC_KEY'],
        private_key=os.environ['BT_PRIVATE_KEY'])
    token = braintree.ClientToken.generate()
    amount = apini.get_amount(payid)
    return render_template('payform.html',
                           amount=amount,
                           token=token,
                           uri=payid)

if __name__ == '__main__':
    print('Starting server...')
    app.run(debug=True)

