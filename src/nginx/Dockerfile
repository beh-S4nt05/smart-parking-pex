FROM nginx:alpine
# O nginx só carrega /etc/nginx/nginx.conf — que por sua vez inclui conf.d/*.conf
# dentro do bloco http{}. O COPY . /etc/nginx/ antigo enterrava o default.conf
# em /etc/nginx/default.conf (fora de contexto, nunca lido): o container subia
# "saudável" servindo o Welcome to nginx cru, sem proxy nenhum para o backend.
RUN rm -f /etc/nginx/conf.d/default.conf
COPY default.conf /etc/nginx/conf.d/default.conf
