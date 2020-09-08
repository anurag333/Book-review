import os
import secrets
import requests
from bs4 import BeautifulSoup

from flask import Flask, session, render_template, request, redirect, url_for, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config["SECRET_KEY"] = "0ei9fu0MXPBHdrsHdWqk1A"

Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def create_session(username):
    token = secrets.token_urlsafe(128)
    db.execute("INSERT INTO cookie (token,username) VALUES (:token,:username)",{"token":token,"username":username})
    db.commit()
    session["token"] = token 

def getImage(isbn):
    page = requests.get(f"https://www.goodreads.com/book/isbn/{isbn}")
    soup = BeautifulSoup(page.text,features="html.parser")
    tag = soup.find("img", id="coverImage")
    tag = str(tag)

    start = tag.find("https:")
    end = tag.find("/>")
    return tag[start:end-1]

@app.route("/")
def index():
    if session.get("token",None) is not None:
        username = db.execute("SELECT username FROM cookie WHERE token = :token",{"token":session["token"]}).fetchone()
        username = username.username
        userdata = db.execute("SELECT username,fname,lname FROM userdata WHERE username = :username",{"username":username}).fetchone()
        recommendations = db.execute("SELECT * FROM book ORDER BY RANDOM() LIMIT 4").fetchall()
        temp =[]
        for reco in recommendations:
            data ={}
            data.clear()
            isbn = reco.isbn
            book_good = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "MG0AsrjunNBMz2QENkZd5w", "isbns": isbn})
            book_good = book_good.json()
            no_of_ratings = book_good['books'][0]['work_ratings_count']
            average_rating = book_good['books'][0]['average_rating']
            
            data['isbn'] = isbn
            data['title'] = reco.title
            data['author'] = reco.author
            data['year'] = reco.year
            data["no_of_ratings"] = no_of_ratings
            data['average_rating'] = average_rating
            data['image_url'] = getImage(isbn)
            temp.append(data)
        recommendations = temp

        return render_template("index.html",userdata = userdata, recommendations=recommendations)
    else:
        return render_template("/login.html")


@app.route("/login", methods = ["POST"])
def login():

    session.clear()

    if request.method == "POST":        
        username = request.form.get("uname")
        password = request.form.get("password")
        
        udata = db.execute("SELECT username,password FROM userdata WHERE username=:username",{"username":username}).fetchone()
        if udata is None:
            return render_template("error.html",message="no such user")
        if udata.password == password:
            print("successful login")
            create_session(username)
            return redirect(url_for('index'))
        else:
            return render_template("error.html",message="password did not match")
    




@app.route("/signup", methods = ["POST"])
def signup():
    username = request.form.get("uname")
    if db.execute("SELECT username FROM userdata WHERE username=:username",{"username":username}).rowcount==0:
        fname = request.form.get("fname")
        lname = request.form.get("lname")
        password = request.form.get("password")
        try:
            db.execute("INSERT INTO userdata (fname,lname,username,password) VALUES (:fname,:lname,:username,:password)",{"fname":fname,"lname":lname,"username":username,"password":password})
        except:
            return render_template("error.html",message = "unable to signup! try again")
        db.commit()
        create_session(username)
        return redirect(url_for('index'))
    else:
        return render_template("error.html",message="user already exist")

@app.route("/signup_page")
def signup_page():
    session.clear()
    return render_template("signup.html")


@app.route("/logout")
def logout():
    if 'token' in session:
        db.execute("DELETE FROM cookie WHERE token=:token",{"token":session['token']})
        db.commit()
        session.pop('token',None)
    return render_template("login.html")


@app.route("/search" , methods =["GET"])
def search():
    search_type = request.args.get('search_type')
    search_string = request.args.get('search_string')
    if search_type != "year":
        search_string = '%'+search_string+'%'
        search_string =search_string.lower()
    
    # result = db.execute("SELECT * FROM book WHERE :search_type LIKE %:search_string%",{"search_type":search_type,"search_string":search_string})
    if search_type == "isbn":
        results = db.execute("SELECT * FROM book WHERE lower(isbn) LIKE :search_string",{"search_string":search_string}).fetchall()
    if search_type == "title":
        results = db.execute("SELECT * FROM book WHERE lower(title) LIKE :search_string",{"search_string":search_string}).fetchall()
    if search_type == "author":
        results = db.execute("SELECT * FROM book WHERE lower(author) LIKE :search_string",{"search_string":search_string}).fetchall()
    if search_type == "year":
        results = db.execute("SELECT * FROM book WHERE year = :search_string",{"search_string":int(search_string)}).fetchall()
    images=[]
    if len(results) <20:
        for result in results:
            image_url = getImage(result.isbn)
            images.append(image_url)



    no_of_results = len(results)
    return render_template('results.html', images=images,results=results, no_of_results = no_of_results)


@app.route("/book/<isbn>")
def book(isbn):
    book_details = db.execute("SELECT * FROM book WHERE isbn= :isbn",{"isbn":isbn}).fetchone()
    book_good = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "MG0AsrjunNBMz2QENkZd5w", "isbns": isbn})
    book_good = book_good.json()
    no_of_ratings = book_good['books'][0]['work_ratings_count']
    average_rating = book_good['books'][0]['average_rating']
    
    reviews = db.execute("SELECT * FROM review WHERE isbn = :isbn",{"isbn":isbn}).fetchall()

    image_url = getImage(isbn)

    return render_template("review.html",image_url= image_url,book_details=book_details,no_of_ratings= no_of_ratings,average_rating=average_rating,reviews=reviews)

@app.route("/sendreview",methods =["POST"])
def sendreview():
    review = request.form.get('review')
    isbn = request.form.get('isbn')
    rating_bukabook = request.form.get('rating')

    token = session['token']
    username = db.execute("SELECT username FROM cookie WHERE token = :token",{"token":token}).fetchone()
    username = username.username
    
    if db.execute("SELECT * FROM review WHERE isbn=:isbn AND username= :username",{"isbn":isbn,"username":username}).rowcount > 0:
        return "already reviewed"
    else:
        db.execute("INSERT INTO review (isbn,username,rating,review) VALUES (:isbn,:username,:rating,:review)",{"isbn":isbn,"username":username,"rating":rating_bukabook,"review":review})
        db.commit()
        return redirect(f"/book/{isbn}")


@app.route("/api/<isbn>")
def api_call(isbn):
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "MG0AsrjunNBMz2QENkZd5w", "isbns": f"{isbn}"})
    res = res.json()
    result ={}
    book = db.execute("SELECT title,author,year FROM book WHERE isbn=:isbn",{"isbn":isbn}).fetchone()
    title = book.title
    author = book.author
    year = book.year

    result['title']= title 
    result['author'] = author
    result['year'] = year
    result['isbn'] = isbn
    result['review_count'] = res['books'][0]['work_reviews_count']
    result['average_score'] = res['books'][0]['average_rating']

    return jsonify(result) 

     
@app.route("/user/<username>")
def user_profile(username):
    userdata = db.execute("SELECT fname,lname,username FROM userdata WHERE username=:username",{"username":username}).fetchone()
    return render_template("user.html",userdata=userdata)
