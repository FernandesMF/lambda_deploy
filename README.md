# lambda_deploy
A python script to help deploying fynctions to aws lambda

## Intended use
I created this code to make it easier to upload code to a lambda instance in aws.
My situtation was that my function would need code from three kinds of sources: 
a library I was developing, external libraries that were available in aws environment,
and external libraries that were not.

This script takes care of making a zip file containing the files from both my library
and the external libraries not available. If you are in a similar situation, I hope it
can help!

## What it does
The script looks at the file with the code that the lambda instance will execute and
does an iterative analysis of the dependencies of the code (which is basically a classification
of the import statements).

Each import statement will be classified in one of the three categories:

- internal dependency (i.e., dependency from another file in my own library)
- external dependency that is supplied by aws
- external dependency that is not supplied by aws

The script keeps track of the internal and not-supplied external dependencies. After running
through all your internal depedencies (iteratively), it makes a local installation of the
non-supplied external deps., and a directory with symblic links to the internal dependencies.

Lastly, it calls a makefile script that will make a zip that is ready to be uploaded and run
by the lambda instance.

## "Enhance your patience"
Lastly, I have to say that this script was made for my specific needs (let's say it was "taylor-made"),
so you may need to tweak things a bit before they work for you. That is especially true for the
makefile script.
