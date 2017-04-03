#!/usr/bin/env python
# coding=utf-8
import os
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort,\
    render_template, flash

app = Flask(__name__)
app.secret_key = '09203ijlkj98883&*&'
app.debug = True


def connect_db():
    rv = sqlite3.connect('data.db')
    rv.row_factory = sqlite3.Row
    return rv


def get_db():
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db


@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()


@app.route('/')
@app.route('/page/<int:page_num>')
def show_entries():
    page_num = request.args.get('page')
    if page_num is None:
        page_num = 1
    else:
    	page_num = int(page_num)
    db = get_db()
    cmd = 'select username, title, text from entries order by id desc limit 5 offset %s;' % (page_num -1)
    print(cmd)
    cur = db.execute(cmd)
    entries = [dict(username=row[0], title=row[1], text=row[2])
               for row in cur.fetchall()]
    if(entries is None):
        return render_template('show_entries.html', entries=[
                               dict(title='No title', text='No text')])
    cur = db.execute( 'select count(*) from entries;')
    pages = cur.fetchone()
    pages = pages[0]
    print(pages)
    return render_template('show_entries.html', entries=entries, pages = range(1, int(pages/5)+2))


@app.route('/add', methods=['GET', 'POST'])
def add_entry():
    if request.method == 'POST':
        if not session.get('logged_in'):
            abort(401)
        db = get_db()
        db.execute('insert into entries (username, title, text) values(?, ?,?);',
                   [session['logged_in'], request.form['title'], request.form['text']])
        db.commit()
        flash('New entry was successfully posted')
        return redirect(url_for('show_profile', username=session['logged_in']))
    return render_template('add_entry.html')    

@app.route('/delete_entry/<int:entry_id>', methods=['GET'])
def delete_entry(entry_id):
    if not session.get('logged_in'):
        abort(401)
    db=get_db()
    db.execute("delete from entries where id=%d and username = (?);" % entry_id, [session['logged_in']])
    db.commit()
    return redirect(url_for('show_profile', username=session['logged_in']))

@app.route('/edit_entry/<int:entry_id>', methods=['GET', 'POST'])
def edit_entry(entry_id):
    if request.method == 'POST':
        db = get_db()
        db.execute("update entries set title=(?) where id=%d;" % entry_id , [request.form['title']])
        db.execute("update entries set text=(?) where id=%d;" % entry_id , [request.form['text']])
        db.commit()
        flash('Blog %s has been updated.' % request.form['title'])
        return redirect(url_for('show_profile', username=session.get('logged_in')))
    db = get_db()
    cur = db.execute(
        "select id, title, text from entries where id=%d" %
        entry_id)
    entryA = cur.fetchone()
    entry = dict(id=entryA[0], title=entryA[1], text=entryA[2])
    return render_template('edit_entry.html', entry=entry)


@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if not session.get('logged_in'):
        abort(401)
    if request.method == 'POST':
        db = get_db()
        cur = db.execute("update users set username='%s', password='%s' where username='%s';" %
                         (request.form['username'], request.form['password'], session.get('logged_in')))
        db.commit()
        cur = db.execute(
            "select id from entries where username='%s';" %
            session.get('logged_in'))
        # May be bug.
        entries = [row[0] for row in cur.fetchall()]
        for entry in entries:
            db.execute(
                "update entries set username='%s' where id=%d" %
                (request.form['username'], entry))
        db.commit()
        flash('Your infomatioin was updated.')
        session['logged_in'] = request.form['username']
        return redirect(
            url_for('show_profile', username=session['logged_in']))
    return render_template('edit_profile.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        db = get_db()
        cur = db.execute("insert into users (username, password) values(?,?);",
                         [request.form['username'], request.form['password']])
        db.commit()
        flash('You were successfully registered.')
        session['logged_in'] = request.form['username']
        return redirect(url_for('show_entries'))
    return render_template('register.html', error=error)


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        db = get_db()
        cur = db.execute("select username, password from users where username='%s' and password='%s'" %
                         (request.form['username'], request.form['password']))
        if(len(cur.fetchall()) > 0):
            session['logged_in'] = request.form['username']
            flash('You were logged in')
            return redirect(url_for('show_entries'))
        else:
            error = 'username or password is invalid.'
    return render_template('login.html', error=error)


@app.route('/profile/<string:username>', methods=['GET', 'POST'])
def show_profile(username):
    db = get_db()
    #username = username.decode('utf-8')
    username = username
    print(username)
    cur = db.execute(
        "select username, password from users where username='%s';" %
        (username))
    row = cur.fetchone()
    user = dict(username=row[0], password=row[1])
    # if(session.get('logged_in') != user['username']):
    #    user['password']= 'Hidden'
    if(user is None):
        return redirect(url_for('login'))
    print(user)
    print(username)

    cur = db.execute(
        "select id, username, title, text from entries where username='%s' order by id desc;" %
        (username))
    entries = [dict(id=row[0], username=row[1], title=row[2], text=row[3])
               for row in cur.fetchall()]
    if(entries is None):
        entries = [dict(title='No blog', text='No blog')]
    return render_template('show_profile.html', user=user, entries=entries)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('show_entries'))


if __name__ == '__main__':
    app.run()
