echo "Enter file-to-copy path"
read source
echo "Enter destination to put file"
read destination

echo "Client 2"
scp "$source" client2:"$destination"

echo "Client 3"
scp "$source" client3:"$destination"

echo "Client 4"
scp "$source" client4:"$destination"

echo "Client 5"
scp "$source" client5:"$destination"