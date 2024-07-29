
REF = $(shell git reflog -q  HEAD -n 1 | cut -d ' ' -f 1)
TAG = $(shell git symbolic-ref -q --short HEAD)
HOST=$(PRODUCT)-$(ENVNAME)
DOMAIN=$(HOST).$(TLD)
DASHDOM=$(subst $e.,-,$(DOMAIN))
APISERVICE=xx-$(DASHDOM)
NEGNAME=$(APISERVICE)-neg # network endpoint group, a gcloud config object
APIBACKEND=$(APISERVICE)-srv # backend service, a gcloud config object
URLMAP=$(APISERVICE)-map # another gcloud config object
TARGETPROXY=$(APISERVICE)-proxy # another gcloud config object
TARGETPROXYSSL=$(APISERVICE)-proxy-ssl # another gcloud config object
IPNAME=$(DASHDOM)-ip
BUCKET=$(DASHDOM)-bucket
BACKBUCK=$(DASHDOM)-backbuck # another gcloud config object
IPADDY=$(shell gcloud compute addresses describe $(IPNAME) --format="get(address)" --global)
INSTANCE_CONNECTION_NAME=$(GC_PROJECT):$(GC_REGION):$(SQL_INSTANCE)
BUILDID = "gcr.io/$(GC_PROJECT)/$(DASHDOM):$(TAG)-$(REF)"


show-build:
	@echo $(BUILDID) .
tailwind:
	@rm -f www/css/site.css
	@npx tailwindcss -i www/css/input.css -o www/css/site.css
static:
	@python scripts/render-static.py
start-proxy:
	GOOGLE_APPLICATION_CREDENTIALS=$(GOOGLE_APPLICATION_CREDENTIALS) ./cloud_sql_proxy --instances=$(GC_PROJECT):$(GC_REGION):$(SQL_INSTANCE)=tcp:5432 > cloud_sql_proxy.log 2>&1 &
psql:
	psql "host=localhost port=5432 sslmode=disable dbname=$(DB_NAME) user=$(DB_USER) password=$(DB_PASS)"
run-dev: static tailwind
	@./scripts/hot-tailwind.sh &
	@./scripts/hot-static.sh &
	pith http localhost 8888 dev
run-prof:
	pith profile localhost 8888 dev
build-container: static tailwind
	docker build -t $(BUILDID) .
run-container:
	docker run \
    -e PORT=80 \
    -e CLOUD_SQL_CONNECTION_NAME=$(INSTANCE_CONNECTION_NAME) \
    -e DB_USER=$(DB_USER) \
    -e DB_PASS='$(DB_PASS)' \
    -e DB_NAME=$(DB_NAME) \
    -e DB_HOST=127.0.0.1 \
    -e DB_PORT=$(DB_PORT) \
    -e API_TOKEN_SALT=$(API_TOKEN_SALT) \
    -e TOTP_ISSUER="'$(TOTP_ISSUER)'" \
    -e JWT_SECRET_KEY="'$(JWT_SECRET_KEY)'" \
    -e PITH_TEMPLATE_DIR='/app/www/' \
    -p 8080:80 $(BUILDID)
container-shell:
	docker run -it $(BUILDID) bash
try-container: build-container run-container
push:
	docker push $(BUILDID)
deploy:
	gcloud run deploy $(APISERVICE) \
		--project $(GC_PROJECT) \
		--image $(BUILDID) \
		--platform managed \
		--memory 8Gi --cpu 4 \
    --add-cloudsql-instances $(INSTANCE_CONNECTION_NAME) \
		--set-env-vars CLOUD_SQL_CONNECTION_NAME=$(INSTANCE_CONNECTION_NAME),DB_USER=$(DB_USER),DB_PASS="$(DB_PASS)",DB_NAME=$(DB_NAME),DB_HOST=/cloudsql/$(INSTANCE_CONNECTION_NAME),DB_PORT=$(DB_PORT),STATIC_URL=$(STATIC_URL),SM_TOKEN="$(SM_TOKEN)",API_TOKEN_SALT="$(API_TOKEN_SALT)",TOTP_ISSUER="$(TOTP_ISSUER)",JWT_SECRET_KEY="'$(JWT_SECRET_KEY)'",PITH_TEMPLATE_DIR=/app/tmpl/,PITH_STATIC_DIR=/app/www
	gcloud run revisions list \
		| grep $(APISERVICE) \
		| head -n 1 \
		| awk '{print $$2}' \
    | xargs -I{} gcloud run services update-traffic $(APISERVICE) --to-revisions {}=100

push-static:
	gsutil rsync -rd www/ gs://$(BUCKET)
	gsutil setmeta -r -h "Cache-control:public, max-age=0" gs://$(BUCKET)
	gsutil iam ch allUsers:objectViewer gs://$(BUCKET)
	gsutil web set -m index.html -e index.html gs://$(BUCKET)
ship: build-container push deploy push-static

create-bucket:
	gsutil mb -b on gs://$(BUCKET)
show-bucket:
	echo $(BUCKET)

reserve-ip:	
	gcloud compute addresses create $(IPNAME) --ip-version=IPV4 --global
	gcloud compute addresses describe $(IPNAME) --format="get(address)" --global
show-ip:
	echo $(IPADDY)
create-zone:
	gcloud dns --project=$(GC_PROJECT) managed-zones create $(ZONE) \
		--description="Zone $(TLD)" \
		--dns-name="$(TLD)." \
		--visibility="public" \
		--dnssec-state="on"
add-record:
	gcloud dns record-sets transaction start --zone=$(ZONE)
	gcloud dns record-sets transaction add $(IPADDY) \
		--name=$(DOMAIN). \
		--ttl=300 \
		--type=A \
		--zone=$(ZONE)
	gcloud dns record-sets transaction execute --zone=$(ZONE)
create-cert:
	gcloud compute ssl-certificates create $(DASHDOM) \
     --description="For $(DOMAIN)" \
     --domains=$(DOMAIN) \
     --global

create-lb:
	gcloud compute backend-buckets create $(BACKBUCK) \
     --gcs-bucket-name=$(BUCKET)
	gcloud compute network-endpoint-groups create $(NEGNAME) \
     --region=$(GC_REGION) \
     --network-endpoint-type=serverless  \
     --cloud-run-service=$(APISERVICE)
	gcloud compute backend-services create $(APIBACKEND) --global

	gcloud compute backend-services add-backend $(APIBACKEND) --global \
     --network-endpoint-group=$(NEGNAME) \
     --network-endpoint-group-region=$(GC_REGION)
	gcloud compute url-maps create $(URLMAP) \
     --default-backend-bucket=$(BACKBUCK)
#	gcloud compute url-maps add-path-matcher $(URLMAP) \
#     --path-matcher-name=matcher \
#     --new-hosts=* \
#     --backend-service-path-rules="/v0/*=$(APIBACKEND)" \
#     --default-backend-bucket=$(BACKBUCK)
	gcloud compute url-maps add-path-matcher $(URLMAP) \
     --path-matcher-name=matcher \
     --new-hosts=* \
     --backend-service-path-rules="/auth/*=$(APIBACKEND),/api/*=$(APIBACKEND)" \
     --delete-orphaned-path-matcher \
     --default-backend-bucket=$(BACKBUCK)
#	gcloud compute target-http-proxies create $(TARGETPROXY) \
#     --url-map=$(URLMAP)
	gcloud compute target-https-proxies create $(TARGETPROXYSSL) \
     --ssl-certificates=$(DASHDOM) \
     --url-map=$(URLMAP)
#	gcloud compute forwarding-rules delete $(DASHDOM)-fwd-rls
	gcloud compute forwarding-rules create $(DASHDOM)-fwd-rls \
     --address=$(IPADDY) \
     --target-https-proxy=$(TARGETPROXYSSL) \
     --global \
     --ports=443


