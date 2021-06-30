function showLocation(province , city , town) {
	
	var loc	= new Location();
	var title	= ['省份' , '地级市' , '市、县、区'];
	$.each(title , function(k , v) {
		title[k]	= '<option value="">'+v+'</option>';
	})
	
	// $('#d1').append(title[0]);
	// $('#d2').append(title[1]);
	// $('#d3').append(title[2]);
	
	$("#d1,#d2,#d3").select2({tags: true, width: "40%"});
	$('#d1').change(function() {
		$('#d2').empty();
		// $('#d2').append(title[1]);
		loc.fillOption('d2' , '0,'+$('#d1').val());
		$('#d2').change()
		//$('input[@name=location_id]').val($(this).val());
	})
	
	$('#d2').change(function() {
		$('#d3').empty();
		// $('#d3').append(title[2]);
		loc.fillOption('d3' , '0,' + $('#d1').val() + ',' + $('#d2').val());
		//$('input[@name=location_id]').val($(this).val());
	})
	
	$('#d3').change(function() {
		$('input[name=location_id]').val($(this).val());
	})
	
	if (province) {
		loc.fillOption('d1' , '0' , province);
		
		if (city) {
			loc.fillOption('d2' , '0,'+province , city);
			
			if (town) {
				loc.fillOption('d3' , '0,'+province+','+city , town);
			}
		}
		
	} else {
		loc.fillOption('d1' , '0');
	}
		
}

$(function(){
		showLocation();
		$('#btnval').click(function(){
			alert($('#d1').val() + ' - ' + $('#d2').val() + ' - ' +  $('#d3').val()) 
		})
		$('#btntext').click(function(){
			alert($('#d1').select2('data').text + ' - ' + $('#d2').select2('data').text + ' - ' +  $('#d3').select2('data').text) 
		})
	})