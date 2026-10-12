#!/bin/bash
echo "Starting data extraction on archive" $1

filename=$1
filenameWithoutExtension=${filename//.gz/}
connexionString=$2

entities=(addresses fares drives plannings users drivers has_fare drive_from drive_to has_drive has_entry has_owner)

createTableAndDataMigrationFromCsv() {
  headers=$1
  headersWithoutQuotes=${headers//\"}
  table=$2
  # Remove quotes and split into array
  IFS=',' read -ra cols <<< "${headersWithoutQuotes}"

  sql="DROP TABLE IF EXISTS $table; CREATE TABLE $table ("

  for col in "${cols[@]}"; do
    sql+="\"$col\" TEXT, "
  done

  # Remove trailing comma and space
  sql=${sql%,*}

  sql+=");"

  echo "$sql" > $table.sql
  echo "\copy $table ($headers) from $table.csv WITH DELIMITER ',' CSV HEADER;" >> $table.sql
}

recordsToPgTable() {
  jq -r '(map(keys) | add | unique) as $cols | map(. as $row | $cols | map($row[.] | tostring )) as $rows | $cols, $rows[] | @csv' $1 > $1.csv
  sed -i '1s/@//g; 1s/.*/\L&/' $1.csv

  # Rename the duplicate column 'type' to 'type2' from the drives table
  if [[ $1 == "drives" ]]; then
    sed -i '1d' drives.csv
    mlr --csv --implicit-csv-header label class,fieldtypes,rid,type,version,comment,created_at,distanceoverride,in_has_drive,name,out_drive_from,out_drive_to,out_has_fare,twoway,type2,updated_at drives.csv > temp.csv
    mv temp.csv drives.csv
  fi

  #Extract csv headers
  headers=$(head -n 1 $1.csv)

  #Create sql create table and from headers
  createTableAndDataMigrationFromCsv $headers $1

  # create the table with psql
  psql $connexionString -c "\i $1.sql"
}

gzip --decompress --keep $filename

# Only records with the @class field interest us
jq '.records' $filenameWithoutExtension > records
jq 'map(select(has("@class")))' records > class

# Extraction of each data class into its own file
 jq 'map(select(."@class" | contains("Address")))' class > addresses
 jq 'map(select(."@class" | startswith("Drive") and endswith("ve")))' class > drives
 jq 'map(select(."@class" | contains("Fare")))' class > fares
 jq 'map(select(."@class" | contains("TaxiPlanning")))' class > plannings
 jq 'map(select(."@class" | contains("User")))' class > users
 jq 'map(select(."@class" | contains("Driver")))' class > drivers

# Extraction of edge classes for relationships
## Enable to link drives and fares
 jq 'map(select(."@class" | contains("has_fare")))' class > has_fare

## Enable to move data from addresses to drives
 jq 'map(select(."@class" | contains("drive_from")))' class > drive_from #drive_and_address
 jq 'map(select(."@class" | contains("drive_to")))' class > drive_to #drive_and_address

## Enable to link drives and clients (users)
 jq 'map(select(."@class" | contains("has_drive")))' class > has_drive #client_and_drive

## Enable to link fares and drivers
 jq 'map(select(."@class" | contains("has_entry")))' class > has_entry #planning and fare
 jq 'map(select(."@class" | contains("has_owner")))' class > has_owner #planning and driver


### Transform jq records into csv
for entityName in "${entities[@]}"; do
    recordsToPgTable $entityName
done

# Migrations
psql $connexionString -c "\i ./migrations/1_fares_drive_rid_from_has_fare.sql"
psql $connexionString -c "\i ./migrations/2_drive_from_to_address_values.sql"
psql $connexionString -c "\i ./migrations/3_drive_client_rid_from_has_drive.sql"
psql $connexionString -c "\i ./migrations/4_fare_driver_from_planning.sql"
psql $connexionString -c "\i ./migrations/5_drives_nature.sql"