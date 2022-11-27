# Hackathon
Агрегатор аптек для города Владивостока

<h3>Инструкция по раскатке:</h3>
Clone repository from github
```
git clone https://github.com/KatantDev/hackathon
cd ./hackathon
```
Build image and start docker container
```
docker build -t api .
docker run -d --name api -p 80:80 api
```