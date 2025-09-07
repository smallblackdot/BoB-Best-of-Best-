import random
import numpy as np

population = 100
# 1. randomly locate 50 victims in range of [0,100]
points = [(random.randint(0, 100), random.randint(0, 100)) for _ in range(population)]

k=int(population/50)

points = np.array(points)
n = len(points)

# Step 1: randomly choose a victim to be shelter location. 
centroids = [points[random.randint(0, n-1)]]

# Step 2-4: choose location for otehr shelter
for _ in range(1, k):
    distances = np.array([min(np.linalg.norm(p-c)**2 for c in centroids) for p in points])
    probabilities = distances / distances.sum()
    chosen_idx = np.random.choice(range(n), p=probabilities)
    centroids.append(points[chosen_idx])

for _ in range(10): 
    cluster = [[] for _ in range(k)]
    # distribute victims into closest shelter (cluster)
    for p in points:
        # 计算这个人和所有 shelter 的距离，找最小的
        distances = [((p[0] - c[0])**2 + (p[1] - c[1])**2)**0.5 for c in centroids]
        nearest = distances.index(min(distances))  # 找到最近的 shelter 的编号
        clusters[nearest].append(p)  # 把这个人放到对应 shelter 组里

    # update the location of shetler
    new_centroids = []
    for group in clusters:
        if group:  # 如果组不为空
            avg_x = sum(p[0] for p in group) / len(group)
            avg_y = sum(p[1] for p in group) / len(group)
            new_centroids.append((avg_x, avg_y))
        else:
            # 如果某个 shelter 没有人，就随机放一个点
            new_centroids.append(random.choice(points))
    
    centroids = new_centroids  # 更新新的 shelter 位置

