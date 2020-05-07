import requests
import urllib
from bs4 import *
import urllib.request
from flask import *
from flask_mysqldb import MySQL
import MySQLdb.cursors
from datetime import datetime
import re

# App config.
DEBUG = True
app = Flask(__name__)
app.config.from_object(__name__)
app.config['SECRET_KEY'] = '7d441f27d441f27567d441f2b6176a'
# Enter your database connection details below
app.config['MYSQL_HOST'] = 'localhost'
#**Please change the following instructions with your localhost username**
app.config['MYSQL_USER'] = 'root'
#**Please change the following instructions with your localhost password**
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'wof'

# Intialize MySQL
mysql = MySQL(app)

def createSoup(url,enc):
	headers = {}
	headers['User-Agent'] = "Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.17 (KHTML, like Gecko) Chrome/24.0.1312.27 Safari/537.17"
	req = urllib.request.Request(url, headers = headers)
	resp = urllib.request.urlopen(req)
	respData = resp.read()
	saveFile = open('index.txt','w',encoding=enc)
	saveFile.write(respData.decode(enc))
	saveFile.close()
	with open("index.txt",'r',encoding=enc) as fp:
		soup = BeautifulSoup(fp.read(),"html.parser")
	return soup 


@app.route("/", methods=['GET', 'POST'])
def search():
	querylist=[]
	cookie=[request.cookies.get('uname')]
	#Do web scraping for the new query
	if request.method == 'POST':
		name=request.form['name']
		#print(name)
		qname='+'.join(name.split(' '))

		queries=['+movies','+tv+shows']

		headers = {}
		headers['User-Agent'] = "Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.17 (KHTML, like Gecko) Chrome/24.0.1312.27 Safari/537.17"

		try:
			#NAME RETRIEVAL
			url='https://www.google.com/search?q='+qname
			soup=createSoup(url,"ISO-8859-1")
			l=soup.find(class_="kno-ecr-pt").get_text()
			temp=l.split(' ')
			name=''
			for x in temp:
				if '(' in x:
					break
				name=name+x+" "
			name=name[:-1]
			print(name)
			querylist.append(name)

			#IMAGE RETRIEVAL 
			#FIRST TRY- WIKIPEDIA DIRECT SEARCH
			try:
				iname='_'.join(name.split(' '))
				url="https://en.wikipedia.org/wiki/"+iname
				print(url)
				soup=createSoup(url,"utf-8")
				l=soup.find("a",{"class":"image"})
				for i in l:
					print(i)
				img=l.find("img")
				alt=img.get("alt")
				if alt!="Disambiguation icon" and img:
					#WIKIPEDIA HAS NO DISAMBIGUATION
					src=img.get("src")
					src="https:"+src
					print(src)
					full_name="static/"+name+".jpg"
					urllib.request.urlretrieve(src,full_name)
					querylist.append(name)
				else:
					raise Exception("No image retreived")
			except:
				try:
					#WIKIPEDIA CONFUSED, GO FOR GOOGLE. 
					url="https://www.google.com/search?q="+qname
					print(url)
					soup=createSoup(url,"ISO-8859-1")
					l=soup.findAll(class_="BA0A6c")
					img=[i.find("img") for i in l]
					src=[i.get("data-src") for i in img]
					source=None
					#CHECK IF ANY IMAGES HAVE DATA SOURCE ATTRIBUTE
					for i in src:
					    if i:
					        source=i
					        break
					#IF YES, GET THAT IMAGE
					if source:
						print(source)
						full_name="static/"+name+".jpg"
						querylist.append(name)
						urllib.request.urlretrieve(source,full_name)
					else:
						raise Exception("No image retreived")
				except:
					querylist.append("anon")


			#LISTS RETREIVAL
			for j in queries:
				url = 'https://www.google.com/search?q='+qname+j
				print(url)
				soup=createSoup(url,"ISO-8859-1")
				l=[x.get_text() for x in soup.findAll(class_="kltat")]
				if not l:
					l=[c.find(class_="title").get_text() for c in soup.findAll(class_="junCMe")]
				if not l:
					l=[c['aria-label'] for c in soup.findAll("a", {"class":"llgymd"})]
				if not l:
					l=[x.get_text() for x in soup.findAll(class_="FLP8od")]
				querylist.append(l)
		except:
			querylist=[None,None,None]
		print("QUERYLIST",querylist)
		try:
			#Check if session["loggedin"] is assigned
			if session["loggedin"]:
				cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
				cursor.execute('INSERT INTO history VALUES (%s, NULL, %s, %s)', (session["id"],datetime.now(),querylist[0],))
				mysql.connection.commit()
		except:
			#If it is not assigned, no login attempt has been made
			session["loggedin"]=False
		return render_template('search.html',list=querylist,search=True)
	#No search query, display search box only
	return render_template('search.html',list=querylist,search=False)
	



@app.route("/login.html", methods=['GET', 'POST'])
def login():
	# Output message if something goes wrong
	msg = ""
	# Check if "username" and "password" POST requests exist
	if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
		# Create variables for easy access
		username = request.form['username']
		password = request.form['password']
		print(username,password)
		# Check if account exists using MySQL
		cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
		cursor.execute('SELECT * FROM accounts WHERE username = %s AND password = %s', (username, password,))
		# Fetch one record and return result
		account = cursor.fetchone()
	# If account exists in accounts table in out database
		if account:
			# Create session data, we can access this data in other routes
			session['loggedin'] = True
			session["id"]=str(account["id"])
			resp = make_response(redirect(url_for("search")))
			resp.set_cookie('uname', account['username'])
			# Redirect to home page
			return resp
		else:
			# Account doesnt exist or username/password incorrect
			msg = 'Incorrect username/password!'
			# Show the login form with message (if any)
	return render_template('login.html', msg=msg)


# http://localhost:5000/logout - this will be the logout page
@app.route('/logout')
def logout():
   # Remove session data, this will log the user out
   session["loggedin"]=False
   session.pop("id",None)
   # Redirect to login page
   return redirect(url_for('search'))

 # http://localhost:5000/register - this will be the registration page
@app.route('/register.html', methods=['GET', 'POST'])
def register():
    # Output message if something goes wrong
    msg = ''
    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        # Create variables for easy access
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
                # Check if account exists using MySQL
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE username = %s', (username,))
        account = cursor.fetchone()
        # If account exists show error and validation checks
        if account:
            msg = 'Account already exists!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers!'
        elif not username or not password or not email:
            msg = 'Please fill out the form!'
        else:
            # Account doesnt exists and the form data is valid, now insert new account into accounts table
            cursor.execute('INSERT INTO accounts VALUES (NULL, %s, %s, %s)', (username, password, email,))
            mysql.connection.commit()
            msg = 'You have successfully registered!'
    elif request.method == 'POST':
        # Form is empty... (no POST data)
        msg = 'Please fill out the form!'
    # Show registration form with message (if any)
    return render_template('register.html', msg=msg)

# http://localhost:5000/profile - this will be the profile page
@app.route('/profile')
def profile():
    # Check if user is loggedin
    if 'loggedin' in session:
        # We need all the account info for the user so we can display it on the profile page
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE id = %s', (session['id'],))
        account = cursor.fetchone()
        # Show the profile page with account info
        return render_template('profile.html', account=account)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))

# http://localhost:5000/history - this will be the history page
@app.route('/history')
def history():
    # Check if user is loggedin
    if 'loggedin' in session:
        # We need all the history for the user so we can display it on the history page
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM history WHERE userid = %s', (session['id'],))
        history = cursor.fetchall()
        print(history)
        # Show the history page with account info
        return render_template('history.html', history=history)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))
if __name__ == "__main__":
    app.run()
