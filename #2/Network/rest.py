from flask import Flask, jsonify, request, make_response, abort
import os
import Network.mySocket as sck
import Database.database as db
import Game.GameMain as gm

import logging
# I'm sick of seeing those requests loggin on my server.
# Ofc, I'll enable it even I need to.
logging.getLogger('werkzeug').disabled = True


def Init():
    global app
    app = Flask(__name__)

    @app.route('/games/started', methods=['GET'])
    def get_started():
        print("Checking if a world has started already...")
        if sck._bridgeConnection['you'] != None: return 'full'
        return 'no' if sck._bridgeConnection['me'] == None else 'yes'

    @app.route('/games/existlist', methods=['GET'])
    def get_existlist():
        print("Looking for Saves...")
        return jsonify(db.GetSaves())

    @app.route('/games/<int:save>/player/<int:p>', methods=['GET'])
    def get_player(save,p):
        print(f"Getting Player {p+1}'s data for Save {str(save + 1)}...") # +1 because save starts at 0, but the display start at 1
        player_data = db.GetCharData(save,p)
        if len(player_data) < 1:
            print(f"Player {p+1} not found. Creating player...")
            db.NewCharData(save,p)
            player_data = db.GetCharData(save,p)
        gm.NewGame(p, request.remote_addr, 5006, save)
        return player_data

    @app.route('/games/getsave', methods=['GET'])
    def get_save():
        print("Telling Player 2 which save to join...")
        return str(gm.WW.CurrentSave[0])

    @app.route('/games/<int:save>/enemyload', methods=['GET'])
    def get_enemy(save=0):
        print("Loading enemies from Save " + str(save + 1) + "...")
        return jsonify(db.GetEnemyData(save))

    @app.route('/games/<string:role>/ready', methods=['POST'])
    def yawn(role=""):
        print(f'Adding "{role}" into server...')
        if role == "me":
            gm.LoadPlayer(0)
        elif role == "you":
            gm.LoadPlayer(1)
            gm.Multiplayer = True
            p1 = gm.WW.Players[0]
            p2 = gm.WW.Players[1]
            sck.SendMessageToClient('me','join,{0},{1},{2}'.format(*p2.GetCenterPosition(),p2.hp))
            sck.SendMessageToClient('you','join,{0},{1},{2}'.format(*p1.GetCenterPosition(),p1.hp))
        else:
            return "False" # Well, I doubt anything will reach here anyways...
        return "True"

def Run():
    global app
    app.run(port='5005', threaded=True)