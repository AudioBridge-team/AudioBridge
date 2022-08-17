while getopts v: flag
do
	case "${flag}" in
		v) version=${OPTARG};;
	esac
done
if [ -z "$version" ]; then
	echo 'ERROR: Version is empty! Set it with argument "-v"'
	exit 1
fi
echo "Version is $version";
