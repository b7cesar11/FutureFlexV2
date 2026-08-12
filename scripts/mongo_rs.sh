#!/bin/bash
# Mantém o MongoDB de /var/lib/mongodb rodando como single-node replica set (rs0)
# na porta 27017, habilitando transações ACID multi-documento sem alterar MONGO_URL.
set -u
supervisorctl stop mongodb >/dev/null 2>&1 || true
pkill -f "mongod --bind_ip_all$" >/dev/null 2>&1 || true
sleep 2

exec_mongo() { mongosh --quiet --eval "$1" 2>/dev/null; }

mongod --bind_ip_all --replSet rs0 --dbpath /var/lib/mongodb \
       --logpath /var/log/mongodb-rs.log --fork >/dev/null 2>&1

for i in $(seq 1 30); do
  exec_mongo 'db.hello()' >/dev/null 2>&1 && break
  sleep 1
done

exec_mongo 'try { rs.status() } catch (e) { rs.initiate({_id:"rs0",members:[{_id:0,host:"127.0.0.1:27017"}]}) }'

for i in $(seq 1 30); do
  [ "$(exec_mongo 'print(db.hello().isWritablePrimary)')" = "true" ] && break
  sleep 1
done
echo "mongo replica set rs0 pronto (primary)"

# mantém o programa vivo para o supervisor
while pgrep -f "mongod --bind_ip_all --replSet rs0" >/dev/null; do sleep 10; done
echo "mongod rs0 encerrado"
exit 1
