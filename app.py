import threading
import random
import time
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ---------- Helper Functions ----------
def Random_x():
    return random.randint(1, 100)

def Random_y():
    return random.randint(1, 100)

def Shelter_distribution(users):
    """
    K-means like distribution for placing shelters based on user locations.
    """
    points = np.array([(u["address_x"], u["address_y"]) for u in users])
    n = len(points)
    k = max(1, int(n / 50))  # at least 1 shelter

    centroids = [points[random.randint(0, n - 1)]]
    for _ in range(1, k):
        distances = np.array([min(np.linalg.norm(p - c) ** 2 for c in centroids) for p in points])
        probabilities = distances / distances.sum()
        chosen_idx = np.random.choice(range(n), p=probabilities)
        centroids.append(points[chosen_idx])

    # K-means iteration
    for _ in range(10):
        clusters = [[] for _ in range(k)]
        for p in points:
            distances = [np.linalg.norm(p - c) for c in centroids]
            nearest = distances.index(min(distances))
            clusters[nearest].append(p)
        new_centroids = []
        for group in clusters:
            if group:
                avg_x = sum(p[0] for p in group) / len(group)
                avg_y = sum(p[1] for p in group) / len(group)
                new_centroids.append((avg_x, avg_y))
            else:
                new_centroids.append(random.choice(points))
        centroids = new_centroids

    return centroids

# ---------- Database ----------
class Database:
    UID = 1
    users = []
    ShID = 1
    shelters = []
    RID = 1
    repository = []
    repository_address_x = Random_x()
    repository_address_y = Random_y()

# ---------- Initialize Users ----------
for _ in range(500):
    user = {
        "UID": Database.UID,
        "name": f"User{Database.UID}",
        "phoneNumber": "N/A",
        "email": "N/A",
        "address_x": Random_x(),
        "address_y": Random_y(),
        "last_request_time": 0,  # 删除 requestLimit
    }
    Database.users.append(user)
    Database.UID += 1

# ---------- Initialize Repository ----------
def init_repository():
    Database.repository.append({
        "RID": Database.RID,
        "repository_name": "Main Repo",
        "address_repository": "Central",
        "address_x": Database.repository_address_x,
        "address_y": Database.repository_address_y,
        "supply": {"general": 100000}  # initial supply
    })
    Database.RID += 1

init_repository()

# ---------- Initialize Shelters ----------
def init_shelters():
    centroids = Shelter_distribution(Database.users)
    for center in centroids:
        shelter = {
            "ShID": Database.ShID,
            "num_of_shelters": 1,
            "address_x": int(center[0]),
            "address_y": int(center[1]),
            "address": f"Shelter {Database.ShID}",
            "supply": 50,
            "demand": 0
        }
        Database.shelters.append(shelter)
        Database.ShID += 1

# ---------- API Routes ----------
@app.route("/api/users")
def api_users():
    return jsonify(Database.users)

@app.route("/api/shelters")
def api_shelters():
    return jsonify(Database.shelters)

@app.route("/api/repositories")
def api_repositories():
    return jsonify(Database.repository)

# Add a new user
@app.route("/add_user", methods=["POST"])
def add_user():
    name = request.form.get("name")
    phoneNumber = request.form.get("phoneNumber")
    email = request.form.get("email")
    address_x = Random_x()
    address_y = Random_y()

    user = {
        "UID": Database.UID,
        "name": name,
        "phoneNumber": phoneNumber,
        "email": email,
        "address_x": address_x,
        "address_y": address_y,
        "last_request_time": 0,  # 删除 requestLimit
    }
    Database.users.append(user)
    Database.UID += 1
    return jsonify({"message": f"User {name} added", "user": user})

# Add new shelters
@app.route("/add_shelter", methods=["POST"])
def add_shelter():
    centroids = Shelter_distribution(Database.users)
    added_shelters = []
    for center in centroids:
        shelter = {
            "ShID": Database.ShID,
            "num_of_shelters": 1,
            "address_x": int(center[0]),
            "address_y": int(center[1]),
            "address": f"Shelter {Database.ShID}",
            "supply": 50,  # initial stock
            "demand": 0,
            "storage_capacity": 50  # NEW: maximum storage limit
        }
        Database.shelters.append(shelter)
        added_shelters.append(shelter)
        Database.ShID += 1
    return jsonify({"message": f"{len(added_shelters)} shelters added", "shelters": added_shelters})

# Add new repository
@app.route("/add_repository", methods=["POST"])
def add_repository():
    repository_name = request.form.get("repository_name")
    address_repository = request.form.get("address_repository")
    repository = {
        "RID": Database.RID,
        "repository_name": repository_name,
        "address_repository": address_repository,
        "address_x": Database.repository_address_x,
        "address_y": Database.repository_address_y,
        "supply": {"general": 100000}
    }
    Database.repository.append(repository)
    Database.RID += 1
    return jsonify({"message": f"Repository {repository_name} added", "repository": repository})

# User requests supply
@app.route("/request_supply", methods=["POST"])
def request_supply():
    UID = int(request.form.get("UID"))
    ShID = int(request.form.get("ShID"))

    user = next((u for u in Database.users if u["UID"] == UID), None)
    shelter = next((s for s in Database.shelters if s["ShID"] == ShID), None)

    if not user or not shelter:
        return "<h2>User or Shelter not found!</h2>"

    if shelter["supply"] > 0:
        shelter["supply"] -= 1
        shelter["demand"] += 1
        user["last_request_time"] = time.time()
        return f"<h2>Supply granted! Shelter {ShID} has {shelter['supply']} supply left. User {UID} requested at {user['last_request_time']}</h2>"
    else:
        return "<h2>Shelter has no supply left!</h2>"

# ---------- Auto supply from repository ----------
def auto_supply_from_repo():
    """
    For each shelter, if (demand + threshold) > supply,
    send supplies from repository in fixed truck loads (20 units each),
    but do not exceed shelter's storage capacity.
    """
    threshold = 20
    repo = Database.repository[0]  # assume single repository

    for shelter in Database.shelters:
        if "storage_capacity" not in shelter:
            shelter["storage_capacity"] = 50

        # Check if this shelter needs resupply
        if shelter["demand"] + threshold > shelter["supply"]:
            if repo["supply"]["general"] <= 0:
                continue  # repository empty, skip

            # Each truck always carries 20 units
            move_amount = min(20, repo["supply"]["general"])

            # Check storage capacity
            available_space = shelter["storage_capacity"] - shelter["supply"]
            if available_space <= 0:
                continue  # shelter is full

            # Final amount = limited by both repo stock and storage space
            move_amount = min(move_amount, available_space)

            # Deliver to shelter
            shelter["supply"] += move_amount
            repo["supply"]["general"] -= move_amount

            # Reduce demand, but not below 0
            shelter["demand"] = max(0, shelter["demand"] - move_amount)

            print(f"delivered {move_amount} supplies from to Shelter {shelter['ShID']} (capacity {shelter['storage_capacity']})")


# ---------- Random requests loop ----------
def random_requests_loop(speed_factor=0.1):
    while True:
        if not Database.users or not Database.shelters:
            time.sleep(0.1 * speed_factor)  # shorter wait if no data
            continue

        user = random.choice(Database.users)
        shelter = random.choice(Database.shelters)

        # Simulate request
        if shelter["supply"] > 0:
            shelter["supply"] -= 1
            shelter["demand"] += 1
            user["last_request_time"] = time.time()
            print(f"User {user['UID']} requested from Shelter {shelter['ShID']}")

        # Auto-supply triggered after request
        auto_supply_from_repo()

        # Faster or slower simulation controlled here
        time.sleep(random.uniform(0.1, 0.5) * speed_factor)


# Start random requests in a separate thread
threading.Thread(target=random_requests_loop, daemon=True).start()

# ---------- Run App ----------
if __name__ == "__main__":
    init_shelters()
    app.run(debug=True)
