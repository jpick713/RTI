
 $( function() {
    var dialog

dialog = $( "#dialog-form" ).dialog({
      autoOpen: false,
      height: 400,
      width: 550,
      modal: true,
      buttons: [{
        text: "OK",
	click: function(){$.post('/comment/{{students.student_name}}', {comment : $('#comment_text').val()}).promise().then()}},
        {text: "Cancel",
	 click: function() {
          dialog.dialog( "close" );
        }
      }]
    });
    
     $( "#add_comment" ).on( "click", function() {
      dialog.dialog( "open" );
    });

})

 
