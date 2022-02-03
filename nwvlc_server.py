from flask import Flask, request, jsonify

app = Flask(__name__)

necc_newsync_fields = []

media_store = {}

def test_list_eq(l1, l2):
    l1.sort()
    l2.sort()
    
    return l1 == l2


def make_act_resp(action, current_ts, synced):
    return jsonify({'action': action, 'current_ts': current_ts, 'synced': synced})


@app.route("/clear_mname_data", methods=["POST"])
def force_assume_sync():
    data = request.json
    if data is not None:
        if 'media_name' in data:
            mname = data['media_name']
            if mname in media_store:
                media_store[mname]['users'] = []
                media_store[mname]['acted_users'] = []
                return jsonify({"result": "removed"})
            return jsonify({"result": "cant find specified media_name"})
    return jsonify({"result": "invalid request"})

@app.route("/poll_status", methods=["POST"])
def handle_nwvlc_req():
    data = request.json

    if data is not None:
        if 'media_name' in data:
            mname = data['media_name']
            if data['media_name'] in media_store:
                # New User
                if data['user'] not in media_store[mname]['users']:
                    media_store[mname]['users'] += [data['user']]
                # User still to sync
                if data['user'] not in media_store[mname]['acted_users']:
                    media_store[mname]['acted_users'] += [data['user']]
                    return make_act_resp(media_store[mname]['action'], media_store[mname]['current_ts'], test_list_eq(media_store[mname]['users'], media_store[mname]['acted_users']))
                # All Users synced
                if test_list_eq(media_store[mname]['acted_users'], media_store[mname]['users']):
                    if data["action"] == "play" or data["action"] == "pause" or data["action"] == "seek":
                        media_store[mname]['action'] = data['action']
                        media_store[mname]['current_ts'] = data['current_ts']
                        media_store[mname]['acted_users'] = [data['user']]
                    return make_act_resp('none', media_store[mname]['current_ts'], test_list_eq(media_store[mname]['users'], media_store[mname]['acted_users']))
                else:
                    print(media_store[mname]['acted_users'])
                    print(media_store[mname]['users'])
                    if data["action"] == "play" or data["action"] == "pause" or data["action"] == "seek":
                        return make_act_resp(media_store[mname]['action'], media_store[mname]['current_ts'], False)
                    return make_act_resp('none', media_store[mname]['current_ts'], False)
            else:
                media_store[mname] = {'current_ts': 0, 'action': 'play', "users": [data['user']], 'acted_users': [data['user']]}
                return make_act_resp('none', media_store[mname]['current_ts'], True)
                
    return jsonify({})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=4270)