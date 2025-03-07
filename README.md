***регистрация***

curl -X POST http://localhost:8000/register -H "Content-Type: application/json" -d '{
  "username": "user2",
  "email": "user2@example.com",
  "password": "password123"
}'

curl -X POST http://localhost:8000/register -H "Content-Type: application/json" -d '{
  "username": "user3",
  "email": "user3@example.com",
  "password": "password456"
}'


***проверка таблицы***

sudo docker exec -it $(sudo docker ps -qf "name=db") psql -U user -d users -c "SELECT * FROM users;"

***получение токена***

curl -X POST http://localhost:8000/login \
-H "Content-Type: application/json" \
-d '{
  "username": "user2",
  "password": "password123"
}'

***проверка токена***

curl -X GET http://localhost:8000/protected-resource -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyMiIsImV4cCI6MTc0MTM3MTk0NH0.k5Hfz8SuahJU_mdtVCkGmyFLCG-PqcnfkxOCFbulkAY"

***получение профиля***

curl -X GET "http://localhost:8000/profile" \
-H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyMiIsImV4cCI6MTc0MTM3MTk0NH0.k5Hfz8SuahJU_mdtVCkGmyFLCG-PqcnfkxOCFbulkAY"

***обновление профиля***

curl -X PUT http://localhost:8000/update-profile \
-H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyMiIsImV4cCI6MTc0MTM3MTk0NH0.k5Hfz8SuahJU_mdtVCkGmyFLCG-PqcnfkxOCFbulkAY" \
-H "Content-Type: application/json" \
-d '{
  "first_name": "Vitya",
  "last_name": "NewLastName",
  "birth_date": "1995-05-21",
  "phone": "+1234567890",
  "email": "newemail@example.com"
}'