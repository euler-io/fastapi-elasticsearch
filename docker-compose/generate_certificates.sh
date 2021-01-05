#!/bin/bash

set -e
    
generate_certificate() {
	local predicate=$1
	local fqdn=$2
	openssl genrsa -out ${OUTPUT}/$predicate-key-temp.pem 2048
	openssl pkcs8 -inform PEM -outform PEM -in ${OUTPUT}/$predicate-key-temp.pem -topk8 -nocrypt -v1 PBE-SHA1-3DES -out ${OUTPUT}/${predicate}-key.pem
	openssl req -new -key ${OUTPUT}/${predicate}-key.pem -out ${OUTPUT}/${predicate}.csr -subj "/C=AU/ST=Some-State/L=AU/O=Internet Widgits Pty Ltd/OU=IWP/CN=${fqdn}"
	openssl x509 -req -in ${OUTPUT}/${predicate}.csr -CA ${OUTPUT}/root-ca.pem -CAkey ${OUTPUT}/root-ca-key.pem -CAcreateserial -sha256 -days 730 -out ${OUTPUT}/${predicate}.pem

    openssl pkcs12 -export -out ${OUTPUT}/${predicate}.p12 -inkey ${OUTPUT}/${predicate}-key.pem -in ${OUTPUT}/${predicate}.pem -passout pass:""
	rm ${OUTPUT}/${predicate}-key-temp.pem
	rm ${OUTPUT}/${predicate}.csr
}

mkdir -p ${OUTPUT}

echo "##############################################################"
echo "#                       Generate Root CA                     #"
echo "##############################################################"
openssl genrsa -out ${OUTPUT}/root-ca-key.pem 2048
openssl req -new -x509 -sha256 -key ${OUTPUT}/root-ca-key.pem -days 730 -out ${OUTPUT}/root-ca.pem -subj "/C=AU/ST=Some-State/L=AU/O=Internet Widgits Pty Ltd/OU=IWP/CN=euler-root"
openssl pkcs12 -export -nokeys -inkey ${OUTPUT}/root-ca-key.pem -in ${OUTPUT}/root-ca.pem -out ${OUTPUT}/root-ca-no-pkey.p12 -passout pass:""

echo "##############################################################"
echo "#                     Generate Admin cert                    #"
echo "##############################################################"
generate_certificate admin admin

echo "##############################################################"
echo "#           Generate Elasticsearch Elasticsearch dev cert    #"
echo "##############################################################"
generate_certificate elastic-dev elastic-dev

echo "##############################################################"
echo "#                     Generate Kibana cert                   #"
echo "##############################################################"
generate_certificate kibana kibana

echo "##############################################################"
echo "#                    Generate Euler API Cert                 #"
echo "##############################################################"
generate_certificate euler euler

rm ${OUTPUT}/root-ca.srl

echo "Files generated at \"$(readlink -f ${OUTPUT})\"."
