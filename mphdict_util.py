# -*- coding: utf-8 -*-

import sys
import sqlite3 as lite

MPH_DICT_DB = 'mph_ua.db'
OUT_DICT_DB = 'out_dict_ua.db'

GOLOSNI = "аеиіоуїєюя"

accent_switcher={5:11,
    6: 12,
    7: 13,
    8: 14,
    9: 15,
    10: 16,
    11: 19,
    12: 20,
    13: 21,
    14: 22,
    15: 23,
    16: 24,
    17: 25,
    18: 26}

class WordBase:
  pass

class WordAccents:

  def __init__(self) -> None:
    self.accents = {}

  def addForGram(self, gram, indents):
    if gram in self.accents:
      val = self.accents[gram]
      if isinstance(val, list):
        self.accents[gram].append(indents)
      else:
        self.accents[gram] = [val, indents]
    else:
      self.accents[gram] = [indents]

  def getIndents(self, gram, idx):
    ret = None
    if gram in self.accents:
      val = self.accents[gram]
      if isinstance(val, list):
        if idx < len(val):
          ret = val[idx]
        else: # get last element
          ret = val[-1]
    return ret

class WordFlexes:

  def __init__(self) -> None:
    self.flexes = {}

  def addFlex(self, fid, flex):
    if fid in self.flexes:
      val = self.flexes[fid]
      if isinstance(val, list):
        self.flexes[fid].append(flex)
      else:
        self.flexes[fid] = [val, flex]
    else:
      self.flexes[fid] = [flex]

def getWordBase(con, nom_old):
  cur = con.cursor()
  cur.execute('select reestr, part, type, accent from nom where nom_old = ?', (nom_old,))
  word = WordBase()
  data = cur.fetchone()
  if data != None and len(data) > 0:
    word.nom_old = nom_old
    word.reestr = data[0]
    word.part = data[1]
    word.type = data[2]
    word.accent = data[3]
    word.inf = word.reestr.replace('"','')
  return word

def findWordBases(con, word):
  cur = con.cursor()
  cur.execute("select reestr, part, type, accent, nom_old from nom where replace(reestr,'\"','') = ?", (word,))
  words = []
  data = cur.fetchall()
  if len(data) == 1 and data[0][0] == 'empty_':
    return words
  else:
    for row in data:
      w = WordBase()
      w.reestr = row[0]
      w.part = row[1]
      w.type = row[2]
      w.accent = row[3]
      w.nom_old = row[4]
      w.inf = w.reestr.replace('"','')
      words.append(w)
  return words

def getIndent(con, type):
  ret = None
  cur = con.cursor()
  cur.execute('SELECT indent FROM indents WHERE type = ?', (type,))
  data = cur.fetchone()
  if data != None and len(data) > 0:
    ret = data[0]
  return ret

def getFlexes(con, type):
  ret = WordFlexes()
  cur = con.cursor()
  cur.execute('SELECT flex, field2 FROM flexes WHERE type = ? ORDER BY field2, id', (type,))
  data = cur.fetchall()
  if len(data) == 1 and data[0][0] == 'empty_':
    return ret
  else:
    for row in data:
      ret.addFlex(row[1], row[0])
  return ret

def getAccents(con, type):
  ret = WordAccents()
  cur = con.cursor()
  cur.execute('''select gram, indent1, indent2, indent3, indent4 
    from accent where accent_type = ?
    order by gram, id''', (type,))
  data = cur.fetchall()
  for row in data:
    ret.addForGram(row[0], row[1:])
  return ret

def convertAccentIndex(ind, part):
  ret = ind
  if part == 35 and ind in accent_switcher: # для доконаних дієслів
    ret = accent_switcher[ind]
  return ret

def getFirstVowelPos(word):
  ret = -1
  for i in range(len(word)):
    if word[i].lower() in GOLOSNI:
      ret = i+1
      break
  return ret

def getVowelCount(word):
  ret = 0
  for i in range(len(word)):
    if word[i].lower() in GOLOSNI:
      ret += 1
  return ret

def isAccentCorrect(word):
  ret = False
  accentPos = word.find('"')
  ret = (accentPos > 0 and word[accentPos-1].lower() in GOLOSNI)
  return ret

def getWordforms(con, word, debug=False, groupFlex=False):
  ret = {}
  accentErrors = False
  indent = getIndent(con, word.type)
  if debug: print("indent: ", indent)
  if indent != None:
    flexes = getFlexes(con, word.type)
    accents = getAccents(con, word.accent)
    if debug: print("accent.id: ", word.accent)
    if debug: print("type: ", word.type)
    baseAccentPos =  word.reestr.find('"')
    # TODO get first vowel (warning if more then one vowels in word)
    if baseAccentPos < 0:
      baseAccentPos = getFirstVowelPos(word.reestr)
      vowelCount = getVowelCount(word.reestr)
      if vowelCount > 1:
        if debug: print("Word {} with {} vowels has not accent.]: ", word.reestr, vowelCount)
    if baseAccentPos < 0: baseAccentPos = 1
    if debug: print("baseAccentPos: ", baseAccentPos)
    wordBase = word.inf
    if debug: print("wordBase: ", wordBase)
    if len(flexes.flexes) > 0:
      for fid, endings in flexes.flexes.items():
        for flexVariant, ending in enumerate(endings):
          if indent == 0:
            wf = wordBase+str(ending or '')
          else:
            wf = wordBase[:-indent]+str(ending or '')
          accentPos = baseAccentPos
          accentFlexNr = convertAccentIndex(fid, word.part)
          indents = accents.getIndents(accentFlexNr, flexVariant)
          if indents is not None:
            if indents[0] is not None:
              accentPos += indents[0]
            else:
              accentErrors = True
              if debug: print('Accent None for {}, {}, flex {}'.format(wordBase, word.nom_old, fid))
          if accentPos > len(wf):
            if getVowelCount(wf) == 1:
              if debug: print("accentPos={} > len(wf) for wf: {}. Use first vowel.".format(accentPos, wf))
              accentPos = getFirstVowelPos(wf)
              wf = wf[:accentPos] + '"' + wf[accentPos:]
            else:
              accentErrors = True
          else:
            if wf[accentPos-1].lower() in GOLOSNI:
              wf = wf[:accentPos] + '"' + wf[accentPos:]
            else:
              if getVowelCount(wf) == 1:
                accentPos = getFirstVowelPos(wf)
                wf = wf[:accentPos] + '"' + wf[accentPos:]
              else:
                accentErrors = True
                if debug: print("Wrong accent {}".format(wf[:accentPos] + '"' + wf[accentPos:]))
                if debug: print("   fid={} (gram={}), flexVariant={}. indents={}".format(fid, accentFlexNr, flexVariant, indents))
          wf = wf.replace('*','').replace('@','').replace('$','').replace('^','').replace('%','')
          if debug: print("  flexes: {} - {} ({}), accent {}".format(fid, ending, wf, accentPos))
          if flexVariant > 0:
            if groupFlex:
              val = ret[fid]
              if isinstance(val, list):
                ret[fid].append(wf)
              else:
                ret[fid] = [val, wf]
            else:
              key = "{}_{}".format(fid, flexVariant)
              ret[key] = wf
          else:
            ret[fid] = wf
    else:
      ret[1]=wordBase
  else:
    print('No indent for '+word.reestr)
  return ret, accentErrors

def genNextFreeKey(dictVar, key):
  i = 1
  ret = "{}_{}".format(key, i)
  while ret in dictVar:
    i += 1
    ret = "{}_{}".format(key, i)
  return ret


def processAllWords(con, conOut, accent=None):
  cur = con.cursor()
  nomSql = 'select nom_old from nom order by nom_old'
  if accent is not None:
    nomSql = 'select nom_old from nom where accent = {} order by nom_old'.format(accent)
  cur.execute(nomSql)
  data = cur.fetchall()
  print("Process {} words".format(len(data)))
  cnt = 0
  accentErrCnt = 0
  for row in data:
    word = getWordBase(con, row[0])
    wfDict = None
    try:
      wfDict, err = getWordforms(con, word)
      if err: accentErrCnt += 1
    except:
      print(sys.exc_info())
      print("Word {}, id {}".format(word.reestr, word.nom_old))
    if wfDict is not None:
      writeWord(conOut, word, wfDict)
    cnt += 1
    if cnt % 5000 == 0:
      print("{} done".format(cnt))
      conOut.commit()
  conOut.commit()
  print("{} words processed\n{} accent errors".format(cnt, accentErrCnt))

def writeWord(con, word, wfDict):
  sqlInf = 'insert into inf(id,type,inf) values (?,?,?)'
  sqlWf = 'insert into wf(fk_inf,wf,fid,accent) values (?,?,?,?)'
  cur = con.cursor()
  cur.execute(sqlInf, (word.nom_old, word.part, word.inf))
  for key, value in wfDict.items():
    accent = value.replace('*','').replace('@','').replace('$','').replace('^','')
    wf = accent.replace('"','')
    fid = str(word.part)+"_"+str(key)
    cur.execute(sqlWf, (word.nom_old, wf, fid, accent))
  # con.commit()

def formatWordAsTable(con, wordId):
  ret = []
  word = getWordBase(con, wordId)
  wfDict, errors = getWordforms(con, word, True, True)
  if word.part in [5,6,7,8,13]:
    ret = formatNounTable(wfDict)
  elif word.part in [11,16]:
    ret = formatAdjTable(wfDict)
  else:
    for key, value in wfDict.items():
      ret.append([key, value])
  return ret

def formatNounTable(wfDict):
  ret = [
    ["Відмінок","Однина","Множина"],
    ["Наз.", wfDict[1], wfDict[8]],
    ["Род.", wfDict[2], wfDict[9]],
    ["Дав.", wfDict[3], wfDict[10]],
    ["Знах.", wfDict[4], wfDict[11]],
    ["Оруд.", wfDict[5], wfDict[12]],
    ["Місц.", wfDict[6], wfDict[13]],
    ["Клич.", wfDict[7], wfDict[14]]]
  return ret

def formatAdjTable(wfDict):
  ret = [
    ["Відмінок","Чол.рід","Жін.рід","Сер.рід","Множина"],
    ["Наз.", wfDict[1], wfDict[7], wfDict[13], wfDict[19]],
    ["Род.", wfDict[2], wfDict[8], wfDict[14], wfDict[20]],
    ["Дав.", wfDict[3], wfDict[9], wfDict[15], wfDict[21]],
    ["Знах.", wfDict[4], wfDict[10], wfDict[16], wfDict[22]],
    ["Оруд.", wfDict[5], wfDict[11], wfDict[17], wfDict[23]],
    ["Місц.", wfDict[6], wfDict[12], wfDict[18], wfDict[24]]]
  return ret

try:
  con = lite.connect(MPH_DICT_DB)
  conOut = lite.connect(OUT_DICT_DB)
  word = getWordBase(con, 78188)
  wfDict = getWordforms(con, word, True, True)
  print(wfDict)
  # print(getVowelPos("гра"))
  # print(getAccents(con, word.accent))
  #writeWord(conOut, word, wfDict)
  #processAllWords(con, conOut)
finally:
  if con:
    con.close()
  if conOut:
    conOut.close()


