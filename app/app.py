from datetime import datetime
from flask import Flask, request, redirect
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from os import environ

app = Flask(__name__)

database_url = environ['DATABASE_URL']
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

mail_env = {'box': environ['MAIL_USERNAME'], 'passwd': environ['MAIL_PASSWORD'], 'server': environ['MAIL_SERVER'],
        'port': environ['MAIL_PORT'], 'recipient': environ['MAIL_RECIPIENT'], 'tls': environ['MAIL_USE_TLS']}
mail = Mail()


class Banlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    IpAddress = db.Column(db.String(15), unique=True, nullable=False)
    DateTime = db.Column(db.String(30), nullable=False)
    UrlPath = db.Column(db.String(15), nullable=False)

    def __init__(self, IpAddress, DateTime, UrlPath):
        self.IpAddress = IpAddress
        self.DateTime = DateTime
        self.UrlPath = UrlPath

    def __repr__(self):
        return '%r, %r, %r, %r' % (self.id, self.IpAddress, self.DateTime, self.UrlPath)


class NoneError(Exception):
    pass


def notify(box, passwd, server, port, recipient, tls, IpAddress):
    ''' Function that sends a notification about a snoopy visitor that managed to block themselves using this app
        It takes as arguments all the credentials necessary to send an email: mailbox (username), password, SMTP server, its port, and a switch for TLS-encrypted connection.
        Additionally, it gets IP address from the request send by the visitor. It is set as a default value, since this function is launched only after the request was made.
    '''
    app.config['MAIL_SERVER'] = server
    app.config['MAIL_PORT'] = port
    app.config['MAIL_USE_TLS'] = tls
    app.config['MAIL_USERNAME'] = box
    app.config['MAIL_PASSWORD'] = passwd

    mail.init_app(app)

    msg = Message("Blocking alert!", sender=box, recipients=[recipient])
    msg.html = '''<h2>Visitor's IP just got blocked!</h2>
                  <p>The IP is {}</p>
               '''.format(IpAddress)
    mail.send(msg)

def getIP():
    if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        return request.environ['REMOTE_ADDR']
    else:
        return request.environ['HTTP_X_FORWARDED_FOR']

@app.route("/")
def index():
    FindIpAddress = getIP()
    IsBlocked = Banlist.query.filter_by(IpAddress=FindIpAddress).first()
    if IsBlocked:
        Date = IsBlocked.DateTime.split(' ')[0]
        Time = IsBlocked.DateTime.split(' ')[1]
        IpAddress = IsBlocked.IpAddress
        return '''Your IP address ({}) was blocked on {} at {} <br />
                  <a href="/unblockme">Unblock me</a>
               '''.format(IpAddress, Date, Time)
    else:
        try:
            if request.args.get('n'):
                '''If n is not empty and it's an integer, this gets a square of supplied integer'''
                n = int(request.args.get('n'))
                x = str(n ** 2)
                return x
            else:
                return ''' <h3>NOTICE: No input provided.</h3>
                           <p>To calculate a square of a specified integer, enter in the address bar the following:</p>
                           <p style="color: blue; font-weight: bold;">http://PYAPP_ADDRESS:8080/?n=x</p>
                           <p>where <b>PYAPP_ADDRESS</b> is IP address of the app, and <b>x</b> is the integer.</p>
                           <p>No floats! 'Cause ain't no one got time for that.</p>
                       '''
        except ValueError:
            n = request.args.get('n')
            return '''What do you think you're doing?<br />
                      This is not an integer:<br />
                      <font color="red" size="100px">{}</font>
                   '''.format(n)


@app.route("/unblockme")
def unblockme():
    FindIpAddress = getIP()
    IsBlocked = Banlist.query.filter_by(IpAddress=FindIpAddress).first()
    if IsBlocked:
        print('Deleting IP {} from ban list'.format(IsBlocked.IpAddress))
        db.session.delete(IsBlocked)
        db.session.commit()
    return redirect("/")


@app.route("/blacklisted")
def blacklisting():
    FindIpAddress = getIP()
    IsBlocked = Banlist.query.filter_by(IpAddress=FindIpAddress).first()
    if not IsBlocked:
        DateTime = datetime.today().replace(microsecond=0)
        UrlPath = str(request.full_path)
        entry = Banlist(FindIpAddress, DateTime, UrlPath)
        print('Blocking IP ' + FindIpAddress)
        db.session.add(entry)
        db.session.commit()
        notify(mail_env['box'], mail_env['passwd'], mail_env['server'],
               mail_env['port'], mail_env['recipient'], mail_env['tls'], FindIpAddress)
    return '', 444


if __name__ == "__main__":
    from waitress import serve
    db.create_all()
    serve(app, host="0.0.0.0", port=8080)
