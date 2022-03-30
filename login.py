from flask import Flask, render_template, request, jsonify, redirect, url_for
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import time
from cryptography.fernet import Fernet

#GEO File
import IP_ADDRESS_TRACKER

from my_model import fuzzy
import mysql.connector
import numpy as np

app = Flask(__name__, template_folder='templates')

usernm = None
f = None
is_help = None
start = None
flag = False
geo_locs = None

@app.route("/<menu>", methods=["GET", "POST"])
def home(menu):
	if request.method == 'POST':
		#print(request.form.to_dict()["data"])
		username = request.form.to_dict()['uname']
		password = request.form.to_dict()['psw']
		#database search
		conn = mysql.connector.connect(host="localhost", port=3306, user="root", passwd="root", database="credentials")
		cur = conn.cursor(buffered=True)
		cur.execute("SELECT username, password FROM credits WHERE username = %s", (username,))
		credential = cur.fetchone()
		if credential == None:
			response = jsonify("invalid")
			print("Response:===============", response)
			return response
		print("Credentials:", credential)

		cur.execute("SELECT threshold FROM credits WHERE username = %s", (username,))
		threshold = cur.fetchone()
		print("Threshold:", threshold[0])
		cur.execute("SELECT user_keys FROM credits WHERE username = %s", (username,))
		keys = cur.fetchone()[0]
		print("Keys:", keys)
		print(type(keys))

		keys = np.array(keys.split(","))

		key_clsf = fuzzy()
		key_clsf.generate_dataset(keys.astype(float))
		if credential[0] == username and credential[1] == password:
			cur.execute("SELECT in_lock FROM credits WHERE username = %s", (username,))
			is_locked = cur.fetchone()
			if is_locked[0] == 0:
				confidence = key_clsf.confidence(np.array(request.form.to_dict()['data'].split(",")), threshold[0])
				print("Confidence:", confidence, "%")

				global geo_locs
				geo_locs = IP_ADDRESS_TRACKER.geo_loc()

				cur.execute("SELECT * FROM " + username)
				temp_data = cur.fetchone()

				geo_data = {}
				all_matched = True
				i = 0
				for key in ['host', 'country', 'public_ip', 'region', 'city']:
					geo_data[key] = temp_data[i]
					i += 1
					print(geo_data[key], geo_locs[key])
					if geo_data[key] != geo_locs[key]:
						all_matched = False
						break

				if confidence > 50 and all_matched:
					cur.execute("UPDATE credits SET logged_in = 1 WHERE username = %s", (username,))
					cur.execute("SELECT logged_in, lock_count FROM credits WHERE username = %s", (username,))
					res = cur.fetchone()
					print("Login Successful!!! Status:", res[0])
					print(type(res[1]))
					if res[1] != 0:
						cur.execute("UPDATE credits SET lock_count = 0 WHERE username = %s", (username,))

				elif all_matched == False and confidence > 50:
					return jsonify("loc_mismatch")

				else:
					cur.execute("SELECT lock_count FROM credits WHERE username = %s", (username,))
					num = cur.fetchone()
					temp_num = num[0] + 1
					if temp_num < 3:
						string = "UPDATE credits SET lock_count = %d" % (temp_num,)
						cur.execute(string + " WHERE username = %s", (username,))
					else:
						cur.execute("UPDATE credits SET in_lock = 1 WHERE username = %s", (username,))
						print("Your Account is locked:(")
						conn.commit()
						cur.close()
						conn.close()
						return jsonify("locked")

			else:
				cur.close()
				conn.close()
				return jsonify("islock")

			conn.commit()
			cur.close()
			conn.close()
			print(confidence)
			val_with_link = {'val': confidence, 'link': url_for('welcome', un_name=username, percent=str(confidence))}
			tru_response = jsonify(val_with_link)
			print("Tru Response:===========", tru_response)
			return tru_response

		else:
			cur.execute("SELECT lock_count FROM credits WHERE username = %s", (username,))
			num = cur.fetchone()
			temp_num = num[0] + 1
			if temp_num < 3:
				string = "UPDATE credits SET lock_count = %d" % (temp_num,)
				cur.execute(string + " WHERE username = %s", (username,))
			else:
				cur.execute("UPDATE credits SET in_lock = 1 WHERE username = %s", (username,))
				print("Your Account is locked:(")
				conn.commit()
				cur.close()
				conn.close()
				return jsonify("locked")

			conn.commit()
			cur.close()
			conn.close()
			return jsonify("mismatch")

	else:
		return render_template("login.html", labl=menu)
		
@app.route("/signup/", methods=["GET", "POST"])
def signup():
	if request.method == "POST":

		key_clsf = fuzzy()

		un = request.form['uname']
		psw = request.form['psw']

		conn = mysql.connector.connect(host="localhost", port= 3306, user="root", passwd="root")
		cur = conn.cursor()
		cur.execute("CREATE DATABASE IF NOT EXISTS credentials")
		cur.execute("USE credentials")
		cur.execute('''CREATE TABLE IF NOT EXISTS
		 credits(Name TINYTEXT NOT NULL, Email TINYTEXT NOT NULL, 
		 username TINYTEXT NOT NULL, password TINYTEXT NOT NULL, 
		 user_keys TEXT NOT NULL, threshold REAL NOT NULL DEFAULT 0.00,
		 logged_in TINYINT NOT NULL DEFAULT 0, lock_count TINYINT NOT NULL DEFAULT 0,
		 in_lock TINYINT NOT NULL DEFAULT 0)''')
		conn.commit()
		cur.execute("SELECT username FROM credits")
		for user in cur.fetchall():
			if user[0] == un:
				return jsonify(1)

		print(request.form.to_dict())
		name = request.form.to_dict()['name']
		email = request.form.to_dict()['email']

		key_pattern = request.form.to_dict()['data']
		print(type(key_pattern))
		cur.execute('''INSERT INTO
		 credits(Name, Email, username, password, user_keys)
		 VALUES (%s, %s, %s, %s, %s)''', (name, email, un, psw, key_pattern))
		conn.commit()

		print("Success!!!")
		temp = np.array(key_pattern.split(",")).astype(float)

		key_clsf.generate_dataset(temp)
		threshold = key_clsf.threshold(temp)

		q = "UPDATE credits SET threshold = %.12f" % (threshold,)
		cur.execute(q + " WHERE username = %s", (un,))
		conn.commit()

		geo_data = IP_ADDRESS_TRACKER.geo_loc()
		cur.execute("CREATE TABLE IF NOT EXISTS " + un + '''(host TINYTEXT NOT NULL, 
			country TINYTEXT NOT NULL, public_ip TINYTEXT NOT NULL, 
			region TINYTEXT NOT NULL, city TINYTEXT NOT NULL)''')
		ins_str = "INSERT INTO " + un
		cur.execute(ins_str + '''(host, country, public_ip, region, city) VALUES
			(%s, %s, %s, %s, %s)''', (geo_data['host'], geo_data['country'], geo_data['public_ip'], geo_data['region'], geo_data['city']))

		conn.commit()
		cur.close()
		conn.close()

		return jsonify(0)

	else:
		return render_template("signup_page.html")

@app.route("/welcome/<un_name>/confd/<percent>/", methods=["GET", "POST"])
def welcome(un_name, percent):
	conn = mysql.connector.connect(host="localhost", port= 3306, user="root", passwd="root", database="credentials")
	cur = conn.cursor()
	cur.execute("SELECT logged_in FROM credits WHERE username = %s", (un_name,))
	test = cur.fetchone()
	cur.execute("SELECT Name FROM credits WHERE username = %s", (un_name,))
	name = cur.fetchone()
	#print("name, type: =================",name[0], type(name[0]))

	if request.method == "POST":
		print(request.form.to_dict())
		switch = request.form.to_dict()['switch']
		if switch == "logout":
			cur.execute("UPDATE credits SET logged_in = 0 WHERE username = %s", (un_name, ))
			cur.execute("SELECT logged_in FROM credits WHERE username = %s", (un_name, ))
			li = cur.fetchone()
			print("Logout Successful !!! Status:", li)
			print(un_name)
			conn.commit()
			
		if switch == "deleted":
			cur.execute("DELETE FROM credits WHERE username = %s", (un_name, ))
			cur.execute("DROP TABLE " + un_name)
			conn.commit()
			print("Account is dropped successfully!!!")
		
		cur.close()
		conn.close()
		return jsonify(0)
	else:
		cur.close()
		conn.close()

		try:
			if test[0] == 1:
				print("User:========", un_name)
				print("Confidence type:", type(percent))
				global geo_locs
				link = url_for('welcome', un_name=un_name, percent=percent)
				return render_template("welcome.html", name=name[0], link=link, perc=percent, geo_data=geo_locs)
		except TypeError:
			pass

		return redirect(url_for('home', menu="login"))


@app.route("/otp_mail/<act>/", methods=["GET", "POST"])
def otp_mail(act):

	if request.method == "POST":
		mailid = request.form.to_dict()['email']
		conn = mysql.connector.connect(host="localhost", port=3306, user="root", passwd="root", database="credentials")
		cur = conn.cursor()
		cur.execute("SELECT Email, username FROM credits WHERE Email = %s", (mailid,))
		found = 0
		record = cur.fetchone()
		try:
			if record[0] == mailid:
				found = 1
				global usernm
				usernm = record[1]

		except TypeError:
			pass

		cur.close()
		conn.close()
		if found == 1:
			from random import randint
			# Generating a 6-digit OTP for password reset
			generate = ""
			once = False
			for i in range(6):
				val = randint(0, 9)
				if not once and val == 0:
					val = 1
					once = True
				generate += str(val)
			key = Fernet.generate_key()
			global f
			f = Fernet(key)
			encrypted_otp = f.encrypt(generate.encode())

			print("AES Key:", key)
			print("Encryped OTP:", encrypted_otp)

			if act == "reset":
				subj = "Password Reset"
				choice = "Reset Password"
			elif act == "unlock":
				subj = "Account Unlock"
				choice = "Unlock Account"

			mail_content = '''Hello,
			This mail is to ''' + choice + '''.
			Your OTP is: ''' + generate + '''. 
			There is only text, no attachments.
			Thank You.'''
			#The mail addresses and password
			sender_address = 'secure.logapp101@gmail.com'
			sender_pass = 'pcnsuuzgcbwxfopi'
			receiver_address = mailid
			#Setup the MIME
			message = MIMEMultipart()
			message['From'] = sender_address
			message['To'] = receiver_address

			message['Subject'] = subj   #The subject line
			#The body and the attachments for the mail
			message.attach(MIMEText(mail_content, 'plain'))
			#Create SMTP session for sending the mail
			session = smtplib.SMTP('smtp.gmail.com', 587) #use gmail with port
			session.starttls() #enable security
			session.login(sender_address, sender_pass) #login with mail_id and password
			text = message.as_string()
			session.sendmail(sender_address, receiver_address, text)
			session.quit()

			return jsonify(url_for('otp_validation', otp=encrypted_otp.decode(), act=act))

		else:
			return jsonify("inval_mail")

	else:
		link_1 = url_for('otp_mail', act=act)
		return render_template("email_val.html", link_1=link_1)


@app.route("/otpval/<otp>/<act>/", methods=["GET", "POST"]) # U need to pass an encrypted otp in URL
# Then u need to decrypt when u validate.
def otp_validation(otp, act):

	global start, flag, f, mailid

	otp_val = f.decrypt(otp.encode())
	otp_val = otp_val.decode()
	
	if request.method == "POST":
		# Continue with otp verification here
		mail_otp = request.form.to_dict()['otp']
		end = time.time()
		if((end - start) / 60 < 10):
			if otp_val == mail_otp:
				flag = False
				print("OTP given in time")
				global is_help
				is_help = True
				if act == "reset":
					response = "password_reset"
				elif act == "unlock":
					conn = mysql.connector.connect(host="localhost", port=3306, user="root", passwd="root", database="credentials")
					cur = conn.cursor()
					unlocker = "UPDATE credits SET in_lock = %d, lock_count = %d" % (0, 0)
					global usernm
					cur.execute(unlocker + " WHERE username = %s", (usernm, ))
					usernm = None
					conn.commit()
					cur.close()
					conn.close()
					response = "unlocked"

				return jsonify(response)

			else:
				return jsonify("invalid")

		else:
			flag = False
			return jsonify("expired")

	else:
		if flag == False:
			flag = True
			start = time.time()

		link = url_for('otp_validation', otp=otp, act=act)
		return render_template("otp_validate.html", link=link)

@app.route("/pass_reset/", methods=["POST", "GET"])
def password_reset():
	global is_help
	if request.method == "POST":
		global usernm
		is_help = False
		pswd = request.form.to_dict()['new_pass']
		keys = request.form.to_dict()['pattern']
		temp = np.array(keys.split(",")).astype(float)

		key_clsf = fuzzy()
		key_clsf.generate_dataset(temp)
		threshold = key_clsf.threshold(temp)
		conn = mysql.connector.connect(host="localhost", port= 3306, user="root", passwd="root", database="credentials")
		cur = conn.cursor()

		update_pswd = "UPDATE credits SET password = '%s'" % (pswd,)
		update_keys = "UPDATE credits SET user_keys = '%s'" % (keys,)
		update_thresh = "UPDATE credits SET threshold = %.12f" % (threshold,)
		cur.execute(update_pswd + " WHERE username = %s", (usernm,))
		cur.execute(update_keys + " WHERE username = %s", (usernm,))
		cur.execute(update_thresh + " WHERE username = %s", (usernm,))
		usernm = None

		conn.commit()
		cur.close()
		conn.close()
		return jsonify("reset_done")

	else:
		if is_help == True:
			return render_template("reset_psw.html")

if __name__ == "__main__":
	app.run(debug=True)