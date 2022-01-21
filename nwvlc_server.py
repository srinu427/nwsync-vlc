from flask import Flask, request, jsonify

app = Flask(__name__)

necc_newsync_fields = []

media_store = {}


@app.route("/poll_status", methods=["GET","POST"])
def handle_nwvlc_req():
    #print(request.data)
    data = request.json
    #print(data)
    #return jsonify({})
    if data is not None:
        if 'media_name' in data:
            if data['media_name'] in media_store:
                if data['user'] not in media_store[data['media_name']]['users']:
                    media_store[data['media_name']]['users'] += [data['user']]
                if data['user'] not in media_store[data['media_name']]['acted_users']:
                    print(media_store[data['media_name']])
                    media_store[data['media_name']]['acted_users'] += [data['user']]
                    return jsonify(media_store[data['media_name']])
                if data["action"] == "play" and media_store[data['media_name']]['acted_users'] != media_store[data['media_name']]['users']:
                    media_store[data['media_name']]['last_action'] = data['action']
                    media_store[data['media_name']]['acted_users'] = [data['user']]
                elif data['action'] == 'pause' and media_store[data['media_name']]['acted_users'] != media_store[data['media_name']]['users']:
                    media_store[data['media_name']]['last_action'] = data['action']
                    media_store[data['media_name']]['current_ts'] = data['current_ts']
                    media_store[data['media_name']]['acted_users'] = [data['user']]
                print(media_store[data['media_name']])
                if media_store[data['media_name']]['acted_users'] == media_store[data['media_name']]['users']:
                    media_store[data['media_name']]['last_action'] = 'none'
                    media_store[data['media_name']]['acted_users'] = []
                return jsonify({'current_ts': 0, 'current_status': 'play', 'last_action': 'none', "users": [data['user']], 'acted_users': [data['user']]})
            else:
                media_store[data['media_name']] = {'current_ts': 0, 'current_status': 'play', 'last_action': 'play', "users": [data['user']], 'acted_users': [data['user']]}
                print({'current_status': 'you_the_first'})
                return jsonify({'current_status': 'you_the_first'})
                    
    return jsonify({})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=4270)