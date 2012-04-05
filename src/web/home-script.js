//Global variables for latitude and longitude of the client
//This is helpful when the user types in 'here' as a value of
//a new property.
var latitude,longitude;

//Simple model to keep the intrinsic Model id property in sync with 
//the '__id' property. This is necessary for actions like destroy 
//which won't be called unless an id is set
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
		
		//populate page with Entry, currently only one with id = 3
		this.model.set("__type","Entry");
		this.model.set("__id","3");
		this.model.fetch();
		
		this.model.on('change', function(){this.render();}, this);
		this.model.on('destroy', function(){
				//TODO: we need to do something when destroy succeeds
			},this);
	},

	//Rendering takes a template and creates the guts of widget.
	render: function(){
		this.el.innerHTML =_.template($('#entity-body').html(), {attributes:this.model.attributes});
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

});