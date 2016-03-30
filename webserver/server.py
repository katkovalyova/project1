#!/usr/bin/env python2.7

"""
Columbia W4111 Intro to databases
Example webserver

To run locally

    python server.py

Go to http://localhost:8111 in your browser


A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""

import os
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response, session, flash

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)


#DATABASEURI = "sqlite:///test.db"
DATABASEURI = "postgresql://acd2164:KAFBXH@w4111db.eastus.cloudapp.azure.com/acd2164"

engine = create_engine(DATABASEURI)

@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request 
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request

  The variable g is globally accessible
  """
  try:
    g.conn = engine.connect()
  except:
    print "uh oh, problem connecting to database"
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass


@app.route('/')
def index():
  return render_template("index.html")

### info of the session kept in app's memory, hashmap mapping cookie to session object
app.config['SESSION_TYPE'] = 'memcached'
app.config['SECRET_KEY'] = 'super secret key'

@app.route('/login', methods=['GET', 'POST'])
def login():
  if request.method == 'POST':
    userid = request.form['uid']
    password = request.form['password']
    cursor = g.conn.execute(text('SELECT * FROM users WHERE userid = :name'), name = userid)
    row = cursor.fetchone()
    if row:
      if password == row[1]:
        session['username'] = userid
        return redirect('/home')
      else:
        context = dict(error = "Incorrect password")
        return render_template("login.html", **context)
    else:
      context = dict(error = "Incorrect username")
      return render_template("login.html", **context)
    cursor.close()
  return render_template("login.html")

@app.route('/signup', methods=['GET', 'POST'])
def signup():
  if request.method == 'POST':
    userid = request.form['uid']
    password = request.form['password']
    cursor = g.conn.execute(text('SELECT * FROM users WHERE userid = :name'), name = userid)
    row = cursor.fetchone()
    if not row:
      g.conn.execute(text('INSERT INTO users VALUES (:name, :pw)'), name = userid, pw = password)
      return redirect('/login')
    else:
      context = dict(error = "Username already exists")
      return render_template("signup.html", **context)
    cursor.close()
  return render_template("signup.html")

@app.route('/home', methods=['GET', 'POST'])
def home():
  userid = session['username']
  cursor = g.conn.execute(text('SELECT q.position, m.title, m.movid FROM queue q, movies m WHERE q.userid = :name AND q.movid = m.movid ORDER BY q.position'), name = userid)
  queue = []
  for result in cursor:
    queue.append(result)
  cursor.close()
  context = dict(queue = queue, blabla = 'blabla', username = userid)
  return render_template("home.html", **context)

@app.route('/removefromqueue', methods=['GET', 'POST'])
def removefromqueue():
  userid = session['username']
  position = int(request.form['pos'])
  maxqueue = g.conn.execute(text('SELECT max(position) FROM queue WHERE userid = :uid'), uid = userid)
  maxqueue = maxqueue.fetchone()[0]
  g.conn.execute(text('DELETE FROM queue WHERE userid = :uid AND position = :pos'), uid = userid, pos = position)
  while (position < maxqueue):
    g.conn.execute(text('UPDATE queue SET position = :pos where userid = :uid AND position = :pos+1'), pos = position, uid = userid) 
    position = position + 1
  return redirect('/home')

@app.route('/managestreamacc', methods=['GET', 'POST'])
def managestreamacc():
  userid = session['username']
  cursor = g.conn.execute(text('SELECT x.extservname, e.extaccun, e.extaccid FROM belongto b, servedby s, externalaccounts e, externalservices x where b.userid = :name AND e.extaccid = b.extaccid AND e.extaccid=s.extaccid AND x.extservid=s.extservid'), name = userid)
  list = []
  for row in cursor:
    list.append(row)
  cursor.close()
  context = dict(username = userid, accounts = list)
  return render_template("managestreamacc.html", **context)

@app.route('/addstreamacc', methods=['GET', 'POST'])
def addstreamacc():
  userid = session['username']
  cursor = g.conn.execute(text('SELECT extservid, extservname FROM externalservices'))
  menu = []
  for row in cursor:
    menu.append(row)
  cursor.close()
  getcontext = dict(menu = menu)
  if request.method == 'POST':
    service = request.form['service']
    exaccun = request.form['exaccun']
    exaccpw = request.form['exaccpw']
    maxaccid = g.conn.execute(text('SELECT max(extaccid) FROM externalaccounts'))
    mid = maxaccid.fetchone()[0]
    cursor = g.conn.execute(text('SELECT a.extaccun FROM externalaccounts a, servedby s WHERE a.extaccun = :un AND a.extaccid = s.extaccid AND s.extservid = :serv'), un = exaccun, serv = service)
    row = cursor.fetchone()
    cursor.close()
    if not row:
      g.conn.execute(text('INSERT INTO externalaccounts VALUES (:id+1, :un, :pw)'), id = mid, un = exaccun, pw = exaccpw)
      g.conn.execute(text('INSERT INTO servedby VALUES (:id+1, :serv)'), id = mid, serv = service)
      g.conn.execute(text('INSERT INTO belongto VALUES (:uid, :id+1)'), uid = userid, id = mid)
    return redirect('/managestreamacc')
  return render_template("/addstreamacc.html", **getcontext)

@app.route('/deletestreamacc', methods=['GET', 'POST'])
def deletestreamacc():
  userid = session['username']
  exaccid = request.form['exaccid']
  g.conn.execute(text('DELETE FROM externalaccounts WHERE extaccid = :eid'), eid = exaccid)
  return redirect('/managestreamacc')

@app.route('/editstreamacc', methods=['GET', 'POST'])
def editstreamacc():
  userid = session['username']
  exaccid = request.form['exaccid']
  
  manage = request.form['manage']
  if manage == 'Delete':
    exaccid = request.form['exaccid']   
    g.conn.execute(text('DELETE FROM externalaccounts WHERE extaccid = :eid'), eid = exaccid)
    return redirect('/managestreamacc')
  if manage == 'Update':
    exaccid = request.form['exaccid']
    print "edit account id = %s \n" % exaccid
    cursor = g.conn.execute(text('SELECT x.extservname FROM servedby s, externalservices x where s.extaccid = :eid and s.extservid = x.extservid'), eid = exaccid)
    esname = cursor.fetchone()
    context = dict(exaccid = exaccid, esname = esname)
    return render_template("/updatestreamacc.html", **context)
  return redirect('/managestreamacc')

@app.route('/replacestreamacc', methods=['GET', 'POST'])
def replacestreamacc():
  try:
    userid = session['username']
    exaccid = request.form['exaccid']
    esname = request.form['esname']
    exaccun = request.form['exaccun']
    exaccpw = request.form['exaccpw']
    print "exaccid = %s\n" % exaccid
    print "esname = %s\n" % esname
    print "exaccun = %s\n" %exaccun
    print "exaccpw = %s\n" %exaccpw
    g.conn.execute(text('UPDATE externalaccounts SET extaccun = :eun, extaccpw = :pw where extaccid = :id'), eun = exaccun, pw = exaccpw, id = exaccid)
  except:
    import traceback; traceback.print_exc()
  return redirect('/managestreamacc')
 

@app.route('/ratemov', methods=['GET', 'POST'])
def ratemov():
  userid = session['username']
  rating = request.form['rating']
  rating = float(rating)
  movid = request.form['movid']
  currate = g.conn.execute(text('SELECT value FROM rate WHERE userid = :uid AND movid = :mid'), uid = userid, mid = movid)
  currate = currate.fetchone()
  if currate:
    g.conn.execute(text('UPDATE rate SET value = :v WHERE userid = :uid AND movid = :mid'), v = rating, uid = userid, mid = movid)
  else:
    g.conn.execute(text('INSERT INTO rate VALUES (:uid, :mid, :v)'), uid = userid, mid = movid, v = rating)
  return redirect('/home')

@app.route('/search', methods=['GET', 'POST'])
def search():
  originput = request.form['search']
  input = '%' + originput + '%'
  
  cursor = g.conn.execute(text('SELECT title, movid FROM movies WHERE LOWER(title) LIKE LOWER(:inpt)'), inpt = input)
  movlist = []
  for row in cursor:
      movlist.append(row)
  cursor.close()

  blank = ' '
  cursor = g.conn.execute(text('SELECT artistfirstname, artistlastname, artistid FROM artists WHERE LOWER(artistfirstname) LIKE LOWER(:inpt) OR LOWER(artistlastname) LIKE LOWER(:inpt) OR LOWER(CONCAT(CONCAT(artistfirstname, :bl), artistlastname)) LIKE LOWER(:inpt)'), inpt = input, bl = blank)
  artlist = []
  for row in cursor:
      artlist.append(row)
  cursor.close()

  cursor = g.conn.execute(text('SELECT genrename, genreid FROM genres WHERE LOWER(genrename) LIKE LOWER(:inpt)'), inpt = input)
  genlist = []
  for row in cursor:
      genlist.append(row)
  cursor.close()

  cursor = g.conn.execute(text('SELECT DISTINCT awardname, year FROM awards WHERE LOWER(awardname) LIKE LOWER(:inpt) OR LOWER(category) LIKE LOWER(:inpt) OR LOWER(role) LIKE LOWER(:inpt) OR LOWER(artist) LIKE LOWER(:inpt)'), inpt = input)
  awlist = []
  for row in cursor:
      awlist.append(row)
  cursor.close()

  context = dict(originput = originput, movies = movlist, artists = artlist, genres = genlist, awards = awlist)
  return render_template("/search.html", **context)

@app.route('/watchhistory', methods=['GET', 'POST'])
def watchhistory():
  userid = session['username']
  cursor = g.conn.execute(text('SELECT m.title, w.datewatched, x.extservname FROM movies m, watched w, externalaccounts e, externalservices x, servedby s, belongto b WHERE m.movid = w.movid AND w.extaccid = e.extaccid AND e.extaccid = b.extaccid AND e.extaccid = s.extaccid AND x.extservid = s.extservid AND b.userid = :username ORDER BY w.datewatched ASC'), username = userid)
  watchlist = []
  for row in cursor:
    watchlist.append(row)
  cursor.close()
  context = dict(watchlist = watchlist, username = userid)
  return render_template("watchhistory.html", **context)

@app.route('/searchhistory', methods=['GET', 'POST'])
def searchhistory():
  userid = session['username']
  cursor = g.conn.execute(text('Select m.title, s.movTimeSearch, m.movid FROM Movies m, searchHistory_Movies s WHERE s.userid= :name AND s.movid=m.movid ORDER BY s.movTimeSearch DESC'), name = userid)
  searchmovList = []
  for result in cursor:
    searchmovList.append((result.title, result[1], result[2]))
  cursor.close()

  cursor2 = g.conn.execute(text('Select a.artistfirstName, a.artistlastname, s.artTimeSearch, a.artistid FROM Artists a, searchHistory_Artists s WHERE s.userid = :name AND  s.artistid=a.artistid ORDER BY s.artTimeSearch DESC'), name = userid)
  searchartList = []
  for result2 in cursor2:
    searchartList.append((result2[0]+' '+result2[1], result2[2], result2[3]))
  cursor2.close()

  context = dict(searchmovList=searchmovList, searchartList = searchartList, username = userid)
  return render_template("searchhistory.html", **context)
  cursor1 = g.conn.execute(text('Select m.title, s.movTimeSearch FROM Movies m, searchHistory_Movies s WHERE s.userid= :name AND s.movid=m.movid ORDER BY s.movTimeSearch DESC'), name = userid)
  searchList = []
  searchList.append(('hello','29'))
  for result in cursor1:
    searchList.append((result.title, result.movTimeSearch))
  cursor1.close()

  context = dict(searchList=searchList, username = userid)
  return render_template("searchHistory.html", **context)

@app.route('/rate', methods=['GET', 'POST'])
def rate():
  userid = session['username']
  cursor = g.conn.execute(text('Select m.title, r.value, m.movid FROM movies m, rate r WHERE r.userid = :name AND  r.movid=m.movid ORDER BY r.value DESC'), name = userid)
  rateList = []
  for result in cursor:
    rateList.append((result.title, result.value, result[2]))
  cursor.close()
  context = dict(rateList=rateList, username = userid)
  return render_template("rate.html", **context) 

@app.route('/browse', methods=['GET', 'POST'])
def browse():
  userid = session['username']
  cursor = g.conn.execute(text('Select m.title, m.year, g.genreName, m.movid FROM Movies m, CategorizedBy c, Genres g WHERE m.movid = c.movid AND c.genreid = g.genreid ORDER BY m.title ASC'))

  movieList = []
  for result in cursor:
    movieList.append((result.title, result.year, result[2], result[3])) 
  cursor.close()
  context = dict(movieList=movieList, username = userid)

  if request.method == 'POST':
    sort = request.form['sort']
    if sort == 'Sort By Title':
      cursor = g.conn.execute(text('Select m.title, m.year, g.genreName, m.movid FROM Movies m, CategorizedBy c, Genres g WHERE m.movid = c.movid AND c.genreid = g.genreid ORDER BY m.title ASC'))
      movieList1 = []
      for result in cursor:
        movieList1.append((result.title, result.year, result[2], result[3]))
      cursor.close()
      context = dict(movieList1=movieList1, username = userid)

    if sort == 'Sort By Year':
      cursor = g.conn.execute(text('Select m.year, m.title, g.genreName, m.movid FROM Movies m, CategorizedBy c, Genres g WHERE m.movid = c.movid AND c.genreid = g.genreid ORDER BY m.year'))
      movieList2 = []
      for result in cursor:
        movieList2.append((result.year, result.title, result[2], result[3]))
      cursor.close()
      context = dict(movieList2=movieList2, username = userid)

    if sort == 'Sort By Genre':
      cursor = g.conn.execute(text('Select g.genreName, m.title, m.year, m.movid FROM Movies m, CategorizedBy c, Genres g WHERE m.movid = c.movid AND c.genreid = g.genreid ORDER BY g.genreName'))
      movieList3 = []
      for result in cursor:
        movieList3.append((result[0], result.title, result.year, result[3]))
      cursor.close()
      context = dict(movieList3=movieList3, username = userid)

  return render_template("browse.html", **context)


@app.route('/movieinfo', methods=['GET', 'POST'])
def movieinfo():
  userid = session['username']
  movieinfoList = []
  movid = request.args.get('movid')
  cursor = g.conn.execute(text('Select m.title, m.year, m.length, m.imdbrating, m.movid from movies m WHERE movid= :movid'), movid = movid)

  for result in cursor:
    movieinfoList.append((result.title, result.year, result.length, result.imdbrating, result.movid)) 
  cursor.close()

  if request.method == 'POST':
    add = request.form['add']
    if add == 'Add To Queue':
      movid = request.form['movid']
      import datetime;  
      date = datetime.date.today()
      maxPos = g.conn.execute(text('SELECT max(position) FROM Queue q  WHERE q.userid= :userid'), userid = userid)
      maxPos = maxPos.fetchone()[0]
      if maxPos:          
        newmax = maxPos + 1
        g.conn.execute(text('insert into queue values (:userid, :movid, :newmax, :date)'), userid=userid, movid=movid, newmax=newmax, date = date)
      else:
        g.conn.execute(text('insert into queue values (:userid, :movid, 1, :date)'), userid=userid, movid=movid, date = date)  
    return redirect("/home") 

  import datetime;  
  date = datetime.datetime.now()
  g.conn.execute(text('INSERT INTO searchHistory_Movies VALUES (:uid, :mid, :date)'), uid = userid, mid = movid, date = str(date))
  
  context = dict(movieinfoList=movieinfoList, username = userid)
  return render_template("movieinfo.html", **context)


@app.route('/artistinfo', methods=['GET', 'POST'])
def artistinfo():
  userid = session['username']
  artistinfoList = []
  artistid = request.args.get('artistid')

  cursor = g.conn.execute(text('Select a.artistfirstName, a.artistlastname, a.dob, a.artistid FROM Artists a WHERE a.artistid= :artistid'), artistid = artistid)
  for result in cursor:
    artistinfoList.append((result[0], result[1], result.dob, result.artistid))  
  cursor.close()

  artistinfoList1 = []
  cursor = g.conn.execute(text('Select m.title, m.movid from Starredin s, Movies m WHERE s.artistid = :artistid AND m.movid = s.movid'), artistid = artistid)
  for result in cursor:
    artistinfoList1.append((result.title, result.movid))  
  cursor.close()
  
  context = dict(artistinfoList=artistinfoList, artistinfoList1=artistinfoList1, username = userid)
  import datetime;  
  date = datetime.datetime.now()
  g.conn.execute(text('INSERT INTO searchHistory_Artists VALUES (:uid, :aid, :date)'), uid = userid, aid = artistid, date = str(date))
  return render_template("artistinfo.html", **context)
  
@app.route('/logout', methods=['GET', 'POST'])
def logout():
  session.pop('username')    
  return redirect('/')


if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using

        python server.py

    Show the help text using

        python server.py --help

    """

    HOST, PORT = host, port
    print "running on %s:%d" % (HOST, PORT)
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)


  run()
