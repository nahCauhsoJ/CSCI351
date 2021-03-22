import mysql.connector
from mysql.connector import errorcode
import json
import time


def Init():
    global mydb
    global mycursor

    try:
        mydb = mysql.connector.connect(
            host="localhost",
            port="3306",
            user="admin",
            passwd="adminpass"
            )

    except mysql.connector.Error as err:
        if err.errno == errcode.ER_ACCESS_DENIED_ERROR:
            print("Something's wrong with your username or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err)

    mycursor = mydb.cursor(buffered=True)
    mycursor.execute("SHOW DATABASES")

    for result in mycursor:
        if "adventuredatabase" in result:
            
            # Merely some code to smite the database as a whole. Normally this will cause a ProgrammingError of Unknown database.
            # Smite only when you need to change the schema of the database.
            #mycursor.execute("DROP DATABASE adventuredatabase")
            
            # Comment out this break if you need to clean the database
            break
            mycursor.execute("USE adventuredatabase")
            mycursor.execute("DELETE FROM playersave")
            mycursor.execute("DELETE FROM enemysave")
            mydb.commit()
            break

    else:
        mycursor.execute("CREATE DATABASE adventuredatabase")
        mycursor.execute("USE adventuredatabase")
        mycursor.execute("CREATE TABLE playersave (name VARCHAR(255), save INT, CONSTRAINT id PRIMARY KEY (name, save), chardata JSON)")
        mycursor.execute("CREATE TABLE enemysave (enemy_id INT, save INT, CONSTRAINT id PRIMARY KEY (enemy_id, save), enemydata JSON)")
    
    mydb = mysql.connector.connect(
            host="localhost",
            port="3306",
            user="admin",
            passwd="adminpass",
            database="adventuredatabase"
            )
    
    mycursor = mydb.cursor(buffered=True)
    print("What the database has (easier grading, I guess...):")
    mycursor.execute("SELECT * FROM playersave")
    print('playersave Table: ', mycursor.fetchall())
    mycursor.execute("SELECT * FROM enemysave")
    print('enemysave Table: ', mycursor.fetchall())
    print()

def GetSaves():
    result = DelayedSelect(f"SELECT save FROM playersave", "GetSaves")
    saves = {"0":False, "1":False, "2":False}
    for i in result:
        saves[str(i[0])] = True
    return saves

def GetCharData(save,p=0):
    player = "me" if p == 0 else "you"
    result = DelayedSelect(f"SELECT chardata FROM playersave WHERE save={save} AND name='{player}'", "GetCharData", all=False)
    return result[0] if result != None else {}

# It'll just throw error at your face if a duplicate entry is found.
def NewCharData(save,p=0):
    player = "me" if p == 0 else "you"
    sql = "INSERT INTO playersave (name, save, chardata) VALUES (%s, %s, %s)"
    val = (player, save, '{"x":320,"y":240,"hp":3}')
    mycursor.execute(sql, val)
    mydb.commit()

def NewEnemyData(save, enemy_id, enemy_data):
    enemy_data = json.dumps(enemy_data)
    result = DelayedSelect(f"SELECT enemy_id FROM enemysave WHERE save={save}", "NewEnemyData")

    if len(result) > 0 and (enemy_id,) in result:
        sql = "UPDATE enemysave SET enemydata = %s WHERE save = %s AND enemy_id = %s"
        val = (enemy_data, save, enemy_id)
    else:
        sql = "INSERT INTO enemysave (enemy_id, save, enemydata) VALUES (%s, %s, %s)"
        val = (enemy_id, save, enemy_data)

    mycursor.execute(sql, val)
    mydb.commit()

    temp_result = DelayedSelect(f"SELECT * FROM enemysave WHERE save={save} AND enemy_id={enemy_id}", "NewEnemyData", all=False)
    result = {}
    for j,k in enumerate(temp_result):
        if j == 0:
            result['enemy_id'] = k
        elif j == 1:
            result['save'] = k
        elif j == 2:
            result['enemy_data'] = json.loads(k)
    return result

# This takes all enemy data while the one in NewEnemyData only returns one. Don't mix up and mess up.
def GetEnemyData(save):
    global mycursor

    temp_result = DelayedSelect(f"SELECT * FROM enemysave WHERE save={save}", "GetEnemyData")
    if temp_result == False:
        return
    
    result = []
    for i in temp_result:
        result.append({})
        for j,k in enumerate(i):
            if j == 0:
                result[-1]['enemy_id'] = k
            elif j == 1:
                result[-1]['save'] = k
            elif j == 2:
                result[-1]['enemy_data'] = json.loads(k)

    return result if len(result) > 0 else {}

"""
def GetCharPos(save,p=0):
    result = GetCharData(save)
    dict = json.loads(result)
    return dict['x'], dict['y']
"""

def SavePlayerData(player_data, save, p=0):
    global mydb
    global mycursor

    player = "me" if p == 0 else "you"
    if 'x' not in player_data or 'y' not in player_data or 'hp' not in player_data or \
        not isinstance(player_data['x'], float) or not isinstance(player_data['y'], float) or not isinstance(player_data['hp'], int):
        print('<Database> Invalid player_data.')
        return False

    result = DelayedSelect(f"SELECT * FROM playersave WHERE save={save} AND name='{player}'", "SavePlayerData",all=False)
    if result == False:
        return False
    elif result == None:
        print("<Database> Can't find this player in the database.")
        return False

    sql = "UPDATE playersave SET charData=%s WHERE save=%s AND name=%s"
    val = (json.dumps(player_data), save, player)
    mycursor.execute(sql, val)
    mydb.commit()

    return True

def SaveEnemyData(enemy_data, save, enemy_id):
    global mydb
    global mycursor

    if 'x' not in enemy_data or 'y' not in enemy_data or 'hp' not in enemy_data or \
        not isinstance(enemy_data['x'], float) or not isinstance(enemy_data['y'], float) or not isinstance(enemy_data['hp'], int):
        print('<Database> Invalid enemy_data.')
        return False

    result = DelayedSelect(f"SELECT enemy_id FROM enemysave WHERE save={save} AND enemy_id='{enemy_id}'", "SaveEnemyData",all=False)
    if result == False:
        return False
    elif result == None:
        print("<Database> Can't find this enemy in the database.")
        return False

    sql = "UPDATE enemysave SET enemydata = %s WHERE save = %s AND enemy_id = %s"
    val = (json.dumps(enemy_data), save, enemy_id)
    mycursor.execute(sql, val)
    mydb.commit()

    return True

# Since many super rare STUUUUUPID Race Conditions stem from the SELECT query, this is a function to give it more chances.
def DelayedSelect(queryyy, err_name, all=True):
    global mycursor

    tries = 5
    fetched = False
    while tries > 0:
        try:
            mycursor.execute(queryyy)
            result = mycursor.fetchall() if all else mycursor.fetchone()
            fetched = True
            break
        except:
            if tries == 5:
                print(f"<Error> A very rare bug of MySQL error just appeared when fetching data in {err_name}. Don't worry. It's not crashing yet.")
            time.sleep(1)
            tries -= 1
    
    if fetched:
        return result # Note that this still returns None if it fetched nothing
    else:
        print("<Error> Database just took a fatal dose of Race Condition when fetching data in {err_name}.")
        return False