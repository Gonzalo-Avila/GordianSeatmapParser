import xml.etree.ElementTree as ElementTree
import json
import sys

error = False

def seatmap_parser_1(tree_root):

	ns = '{http://www.opentravel.org/OTA/2003/05/common/}'

	seat_map_response = tree_root.find('.//{http://www.opentravel.org/OTA/2003/05/common/}SeatMapResponse')

	flight_info = seat_map_response.find(ns+'FlightSegmentInfo')
	flight = {}
	flight['flightNumber'] = flight_info.attrib.get('FlightNumber')
	flight['departureTime'] = flight_info.attrib.get('DepartureDateTime')
	flight['departureLocation'] = flight_info.find(ns + 'DepartureAirport').attrib.get('LocationCode')
	flight['arrivalLocation'] = flight_info.find(ns + 'ArrivalAirport').attrib.get('LocationCode')

	rows = []
	rows_info = seat_map_response.iter(ns + 'RowInfo')

	for row_info in rows_info:

		row_number = row_info.attrib.get('RowNumber')
		row = {'rowNumber': row_number, 'cabinClass': row_info.attrib.get('CabinType')}
		seats = []

		seats_info = row_info.iter(ns + 'SeatInfo')
		for seat_info in seats_info:
			summary = seat_info.find(ns + 'Summary')
			service = seat_info.find(ns + 'Service')
			seat = {
				# Apparently there's no info related to element type in the sample files, so I used a default value
				'type': 'Seat',
				'id': summary.attrib.get('SeatNumber'),
				'available': summary.attrib.get('AvailableInd'),
				# Not every seat has a price, only the available ones
				'price': service.find(ns + 'Fee').attrib.get('Amount') if service is not None else 'NA',
				# I tried to keep the same structure for both output files, saving some custom relevant fields in here
				'additionalInfo': {
					'planeSection': seat_info.attrib.get('PlaneSection'),
					'inExitRow':  seat_info.attrib.get('ExitRowInd')
				}
			}
			seats.append(seat)

		row['seats'] = seats
		rows.append(row)

	flight['rows'] = rows

	return flight

def seatmap_parser_2 (tree_root):

	ns = '{http://www.iata.org/IATA/EDIST/2017.2}'

	# This data is used later to retrieve properties for each seat
	offer = tree_root.find(ns + 'ALaCarteOffer')
	offers = {}
	for offer_item in offer:
		offers[offer_item.attrib.get('OfferItemID')] = offer_item.find('.//' + ns + 'SimpleCurrencyPrice').text

	seat_definion_list = tree_root.find('.//' + ns + 'SeatDefinitionList')

	flight = {}
	departure_info = tree_root.find('.//' + ns + 'Departure')
	flight['flightNumber'] = tree_root.find('.//' + ns + 'FlightNumber').text
	flight['departureTime'] = departure_info.find(ns + 'Date').text + departure_info.find(ns + 'Time').text
	flight['departureLocation'] = departure_info.find(ns + 'AirportCode').text
	flight['arrivalLocation'] = tree_root.find('.//' + ns + 'Arrival').find(ns + 'AirportCode').text

	rows = []
	rows_info = tree_root.iter(ns + 'Row')

	for row_info in rows_info:

		row_number = row_info.find(ns + 'Number').text
		row = {'rowNumber': row_number, 'cabinClass': 'NA'}
		seats = []
		seats_info = row_info.iter(ns + 'Seat')

		for seat_info in seats_info:

			seat_definition_ids = list(map(lambda s_info: s_info.text, seat_info.findall(ns + 'SeatDefinitionRef')))

			seat_has_definition = lambda s_def: s_def.attrib.get('SeatDefinitionID') in seat_definition_ids
			seat_definitions = list(filter(seat_has_definition,seat_definion_list))

			seat_properties = list(map(lambda s_def: s_def.find('.//' + ns + 'Text').text, seat_definitions))

			seat_offer_ref = seat_info.find(ns + 'OfferItemRefs')

			seat = {
				# Apparently there's no info related to element type in the sample files, so I used a default value
				'type': 'Seat',
				'id': row_number + seat_info.find(ns + 'Column').text,
				'available': str('SD4' in seat_definition_ids),
				# In this file seat prices seem to depend on associated offers, and not every seat has one of them
				'price': offers[seat_offer_ref.text] if seat_offer_ref is not None else 'NA',
				# I tried to keep the same structure for both output files, saving some custom relevant fields in here
				'additionalInfo': {
					'seatProperties': seat_properties
				}
			}
			seats.append(seat)

		row['seats'] = seats
		rows.append(row)

	flight['rows'] = rows

	return flight

def parse_seatmap_to_json(file_to_parse):

	element_tree = ElementTree.parse(file_to_parse)
	tree_root = element_tree.getroot()

	valid_parser = {
		'seatmap1.xml': seatmap_parser_1,
		'seatmap2.xml': seatmap_parser_2
	}

	flight_data = valid_parser[file_to_parse](tree_root)

	output_file = file_to_parse.replace('.xml', '_parsed.json')

	with open(output_file, "w") as parsed_seatmap_file:
		json.dump(flight_data, parsed_seatmap_file, indent=4)

try:
	file_to_parse = None
	file_to_parse = sys.argv[1]
except:
	print('Invalid argument')
	error = True

if file_to_parse:
	try:
		parse_seatmap_to_json(file_to_parse)
	except Exception as e:
		print(str(e))
		error = True

if not error:
	print('Seatmap file parsed successfully')
else:
	print('Seatmap file could not be parsed')
