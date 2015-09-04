docker build  -t nherbaut/worker-full .; docker save nherbaut/worker-full| sudo ./docker-squash -t nherbaut/worker -verbose | docker load; docker push  nherbaut/worker
