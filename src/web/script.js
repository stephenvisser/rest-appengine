//Global variables for latitude and longitude of the client
//This is helpful when the user types in 'here' as a value of
//a new property.
var latitude,longitude;

//These are shortcuts that users can type to enter special things
var typeOptions = ['null', 'true', 'false', 'here', 'now'],


ModalNamer = Backbone.View.extend({
	//This is the constructor of the view. From other tutorials, 
	//it's common shorthand just to render the view.
	initialize: function(){
		this.render();
	},
	//These two attributes define the type of HTML element this
	//view is
	tagName: 'div',
	className: 'modal fade',
	//This defines what happens when this view is rendered.
	render: function(){
		//This takes a template from our HTML file and creates 
		//The modal HTML from this markup
		this.el.innerHTML = $('#modal-body-template').html();
		var nameInput = this.$('input');
		//In order to move the focus to the main input box when
		//the modal is shown, we bind to the bootstrap event 'shown'
		this.$el.on('shown', function (event) {
			nameInput.focus();});
	},
	//These events represent any handling that the view needs
	//The only event we're interested in is when the allDone button
	//is pressed
	events: {"click button": "allDone",
		//We also provide the user with a shortcut to press the enter
		//key as an alternate way to exit
		"keypress input": function(event){
			if (event.which == 13)
			{
				this.allDone();
			}
		}},
		//Simply set the type of the current model entity and then hide
		allDone: function(){
			this.model.set("__type",this.$('input').val());
			this.$el.modal('hide');
		}
});

//Our model couldn't be simpler. The only thing we need done is to keep
//the intrinsic Model id property in sync with the '__id' property.
//This is necessary for actions like destroy which won't be called unless
//an id is set
ModelEntity = Backbone.Model.extend({
	initialize:function(options){
		this.on('change:__id',function(){
			this.id = this.get('__id');   
		});
	}
});

//This is the main widget of our application
EntityWidget = Backbone.View.extend({
	initialize:function(options){
		this.render();
		//We listen to the change and destroy backbone events on
		//the model
		this.model.on('change', function(){this.render();}, this);
		this.model.on('destroy', function(){
				//TODO: we need to do something when destroy succeeds
			},this);
	},
	//This is a div HTML element at its core
	tagName:'div',
	//These are the important events this widget handles
	events: {
	//This creates a new property in our model object when the 
	//'add' button is pressed	
	"click .add-property":function(){
		this.add();
	},
	//This saves the object to the server when the save button
	//is pressed
	"click .save":function(){
		this.model.save();
	}, 
	//This fetches the object with the given '__id' property
	//effectivly syncing our client-side model with what the server has
	"click .retrieve":function(){
		this.model.fetch();
	},
	//This will destroy the object on the server that has the given
	//'__id'. The client-side object should stick around though in
	//case we change our mind
	"click .delete":function(){
		this.model.destroy();
	},
	//This will add the property when 'enter' is pressed
	"keypress #new-value":function(event){
		if (event.which == 13)
		{
			this.add();
			return false;
		}
	},
	//This is called when the autocomplete box is pressed
	"change #new-value":function(event){
		this.check(event.target.value);
	},
	//This is called every time a character is pressed on keyboard
	"input #new-value":function(event){
		this.check(event.target.value);		
	}},
	//This does some cool stuff to format the value string so that
	//the user knows they are entering an appropriately formatted 
	//property
	check:function(currentText){
		for (var anOption in typeOptions)
		{
			if (currentText == typeOptions[anOption])
			{
				this.$('#value-control').addClass("success");
				this.$('#value-control').find('.help-inline').html('-> ' + typeOptions[anOption]);
				return;
			}			
		}
		
		//Check for numbers too
		if(/^\d+$/.test(currentText))
		{
			this.$('#value-control').addClass("success");
			this.$('#value-control').find('.help-inline').html('-> int');
			return;
		}
		else if(/^\d*\.\d+$/.test(currentText))
		{
			this.$('#value-control').addClass("success");
			this.$('#value-control').find('.help-inline').html('-> float');
			return;
		}
		
		//If there is no match, remove formatting
		this.$('#value-control').removeClass("success");
		this.$('#value-control').find('.help-inline').html('');
	},
	add:function()
	{
		//Parse the type as appropriate and then set the model
		result = this.$('#new-value').val();
		if (result=="null")
			result = null;
		else if(result=="true")
			result = true;
		else if(result =="false")
			result = false;		
		else if(result=="here")
		{
			result = latitude.toString()+ "," + longitude.toString();
		}
		else if(result=="now")
		{
			result = new Date().toISOString();
		}
		else if(/^\d+$/.test(result))
		{
			result = parseInt(result, 10);		
		}
		else if(/^\d*\.\d+$/.test(result))
		{
			result = parseFloat(result);      
		}
		this.model.set(this.$('#new-key').val(), result);
	},
	//Rendering takes a template and creates the guts of widget.
	render: function(){
		this.el.innerHTML =_.template($('#entity-body').html(), {attributes:this.model.attributes});
		//Set the typeahead so the user is aware of some of the options
		//available to him
		var something1 = this.$('#new-value').typeahead({source: typeOptions});
		//Sets the focus to the key box every time the widget is rendered.
		this.$('#new-key').focus();
	}
});

//The sync class is what backbone uses to sync to the server. It 
//uses a weird method, so I'm doing all the $.ajax calls manually.
Backbone.sync = function(method, model) {
	//We treat update and create calls the same since we overwrite 
	//server values each time.
	//TODO: Error conditions are currently not handled. We need to fix
	//this.
	if (method == "create" || method=="update")
	{
		//Creates the post request and then sets the id on success.
		$.ajax({type:"POST",contentType:"application/json", data:JSON.stringify(model),url:'/api',success:function(data, textStatus, jqXHR){
			model.set("__id",parseInt(data, 10));
		}});
	}
	else if (method=="delete")
	{
		//Creates the delete request
		$.ajax({type:"DELETE",url:'/api/'+model.get('__type')+'/'+model.get('__id')});
	}
	else
	{
		//Creates the get request and populates all fields upon success
		$.ajax({url:'/api/'+model.get('__type')+'/'+model.get('__id'), success:function(data, textStatus, jqXHR){
			model.set(data);
			}
		});
	}

};

//JQuery to english: 'When the page is done loading, perform this function'
$(function(){
	//Find our current location. This will not work on all browsers,
	//so we should do more checking here eventually.
	navigator.geolocation.getCurrentPosition(function (position) {
		latitude = position.coords.latitude;
		longitude = position.coords.longitude;
	});
	
	//Create the current model which doesn't have anything yet.
	var currentModel = new ModelEntity();

	//Create the widget that manages the model
	var newWidget = new EntityWidget({model:currentModel});
	
	//Add the widget to the body.
	$('body').append(newWidget.el);

	//Create the modal immediately
	new ModalNamer({model:currentModel}).$el.modal('show');
});