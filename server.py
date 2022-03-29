import os
import sys, traceback
from flask import Flask, request, render_template, flash, redirect
import sqlite3 as lite
import mphdict_util

MPH_DICT_DB = 'mph_ua.db'
OUT_DICT_DB = 'out_dict_ua.db'

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
  if request.method == 'POST':
    err_msg = None
    word = request.form['word']
    query_content = "{}".format(word)
    con = lite.connect(MPH_DICT_DB)
    resultList = mphdict_util.findWordBases(con, word)
    if con:
      con.close()

    return render_template('index.html',
                            err_msg=err_msg,
                            query_content=query_content,
                            resultList=resultList)
  else:
    return render_template('index.html')

@app.route('/flex', methods=['GET'])
def flex():
  err_msg = None
  wordId = request.values['wordId']
  # query_content = "wordId: {}".format(wordId)
  con = lite.connect(MPH_DICT_DB)
  flexList = mphdict_util.formatWordAsTable(con, wordId)
  return render_template('flex.html', err_msg=err_msg, flexList=flexList)

@app.route('/convert_db', methods=['GET'])
def convert_db():
  err_msg = None
  try:
    con = lite.connect(MPH_DICT_DB)
    conOut = lite.connect(OUT_DICT_DB)
    mphdict_util.createOutTables(conOut)
    mphdict_util.processAllWords(con, conOut)
  finally:
    if con:
      con.close()
    if conOut:
      conOut.close()
  return render_template('util.html', err_msg=err_msg)

if __name__=="__main__":
  app.run("0.0.0.0")
