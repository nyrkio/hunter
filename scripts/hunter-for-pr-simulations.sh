#!/bin/bash


PVALUES="0.0 0.001 0.005 0.01 0.02 0.03 0.04 0.05 0.1 0.2"
THRESHOLD="0.0"
PRDIFF="0 1 2 3 4 5 10 20 50 100 150 200 300 500 700 900 1000 2000 5000 10000 20000 30000 50000 100000 200000 500000 1000000 5000000 10000000 20000000 50000000 100000000"
WINDOW="50 25 20 10"
echo > rp.outfile

for P in $PVALUES
do
  for T in $THRESHOLD
  do
    for W in $WINDOW
    do
        for D in $PRDIFF
        do
            PRMEDIAN=$((125196996+$D)).33333337
            #PRMEDIAN=125190906.68888888
            PRMAX=$((27404853+$D)).33334444
            cp rp.template rp.prtest
            echo '
            {
                "timestamp": 1708135592,
                "metrics": [
                {
                    "name": "inst",
                    "value": '${PRMEDIAN}',
                    "unit": "inst"
                },
                {
                    "name": "median",
                    "value": 27356866,
                    "unit": "ns"
                },
                {
                    "name": "min",
                    "value": 27091224.388888888,
                    "unit": "ns"
                },
                {
                    "name": "max",
                    "value": '${PRMAX}',
                    "unit": "ns"
                },
                {
                    "name": "mad",
                    "value": 47987.22222222388,
                    "unit": "ns"
                }
                ],
                "attributes": {
                "git_commit": "30a1ca355782136834ced645e04a9ad01ecb3a7b",
                "branch": "dev",
                "git_repo": "https://github.com/acme/gadgets"
                }
            }
            ' >> rp.prtest
            echo ']' >> rp.prtest


            CMD="poetry run hunter analyze -P $P -M $T --window $W --output json rp.prtest"
            STATS="D=$D -> inst=$PRMEDIAN ("$((($D*1000000000)/125196996))")    ns max=$PRMAX ("$((($D*1000000000)/27404853))")"
            echo $CMD
            echo $STATS
            echo >> rp.outfile
            echo $CMD  >> rp.outfile
            echo $STATS >> rp.outfile
            $CMD >> rp.outfile
      done
    done
  done
done


# Post processing to CSV and google sheet
# N=2
# cp rp.outfile rp.outfile.$N
# grep -B 4 1708135592 rp.outfile.$N> rp.outfile.$N.positive
# grep -B 4 1708135592 rp.outfile.$N |grep -v Computing|grep -v time |grep -v '^--'|grep poetry |cut -d ' ' -f 6,8,10> rp.outfile.$N.params.csv
# grep -B 4 1708135592 rp.outfile.$N |grep -v Computing|grep -v time |grep -v '^--'|grep D| cut -d ' ' -f 1,4,7| tr --delete 'D=()'> rp.outfile.$N.values.csv
# for line in $(grep -B 4 1708135592 rp.outfile.$N |grep -v Computing|grep -v poetry|grep -v D|tac -s " "|tr ' ' '_' ); do echo $line|grep -v '^--'; echo;done|cut -d "_" -f 6,7,8,9,10,11,12,13,14,15 --output-delimiter ' '|grep after|cut -d ' ' -f 1,4,7,10|tr --delete '",'> rp.outfile.$N.stats.csv
#
# kate rp.outfile.$N.*.csv
# copy paste to spreadsheet



