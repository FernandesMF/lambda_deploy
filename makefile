# tree -ifF --noreport package_symlinks/ | grep -v /$ # still need to follow links, turn off report

# make a variable with the directory name

# unit test this guy? it should make a new zip if i change some of the internal dependencies...
preprocessing.zip: audience_id.txt preprocessing.py preprocessing.cfg $(tree -ifF --noreport packaging_area/ | grep -v /$)
	cd packagig_area; \
	zip ../take_me_to_your_lambda.zip -r ./*
	zip take_me_to_your_lambda.zip.zip -g lambda_execution_file.py

