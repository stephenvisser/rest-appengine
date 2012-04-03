var latitude,longitude;

ModalNamer = Backbone.View.extend({
    initialize: function(){
        this.render();
    },
    tagName: 'div',
    className: 'modal fade',    
    render: function(){
        this.el.innerHTML = $('#modal-body').html();
        var nameInput = this.$('input');
        this.$el.on('shown', _.bind(function (event) {
            nameInput.focus()},this));
    },
    events: {"click button": "allDone",
    "keypress input": function(event){
        if (event.which == 13)
        {
        	this.allDone();
       	}
    }},
    allDone: function(){
    	var newWidget = new EntityWidget({model:new ModelEntity({__type:this.$('input').val()})});
        $('body').append(newWidget.el);
        this.$el.modal('hide');
    }
})

ModelEntity = Backbone.Model.extend({
	   initialize:function(options){
		   this.on('change:__id',function(){
			    this.id = this.get('__id');   
		   });
	    }
});

EntityWidget = Backbone.View.extend({
	initialize:function(options){
        this.render();
        this.model.on('change', function(){this.render()}, this);

	},
	tagName:'div',
    events: {"click .add-property":function(){
        this.add();
    }, 
    "click .save":function(){
        this.model.save();
    }, 
    "click .retrieve":function(){
        this.model.fetch();
    }, 
    "click .delete":function(){
        this.model.destroy();
    }, 
    "keypress #new-value":function(event){
    	if (event.which == 13)
    	{
    	    this.add();
    		return false;
    	}
    },
     "change #new-value":function(event){
    	var currentText = event.target.value;
        if (currentText=="null" || currentText=="true" || currentText=="false" || currentText=="here" || currentText=="now")
        {
        	this.$('#value-control').addClass("success");
        }
        else
        {
        	this.$('#value-control').removeClass("success");
       	}
    },
    "input #new-value":function(event){
        var currentText = event.target.value;
        if (currentText=="null" || currentText=="true" || currentText=="false" || currentText=="here" || currentText=="now")
        {
            this.$('#value-control').addClass("success");
        }
        else
        {
            this.$('#value-control').removeClass("success");
        }

    }},
    add:function()
    {
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
    	else if(/\d+/.test(result))
    	{
    	    result = parseInt(result);		
    	}
        else if(/\d*\.\d+/.test(result))
        {
            result = parseFloat(result);      
        }
        this.model.set(this.$('#new-key').val(), result);
    },
    render: function(){
        this.el.innerHTML =_.template($('#entity-body').html(), {attributes:this.model.attributes});
        var typeOptions = ['null', 'true', 'false', 'here', 'now'];
        var something1 = this.$('#new-value').typeahead({source: typeOptions});
        this.$('#new-key').focus();
    }
})

Backbone.sync = function(method, model) {
	if (method == "create" || method=="update")
	{
	    var readyForJSON = JSON.stringify(model);
	    $.ajax({type:"POST",contentType:"application/json", data:readyForJSON,url:'/api',success:function(data, textStatus, jqXHR){
	        model.set("__id",parseInt(data));	    	
	    }});
	}
	else if (method=="delete")
	{
	      $.ajax({type:"DELETE",url:'/api/'+model.get('__type')+'/'+model.get('__id')});
	}
	else
	{
        $.ajax({url:'/api/'+model.get('__type')+'/'+model.get('__id'), success:function(data, textStatus, jqXHR){        	
            model.set(data);   
        }

        });
	}
		
};

//JQuery to english: 'When the page is done loading, perform this function'
$(function(){
    navigator.geolocation.getCurrentPosition(function (position) {
        latitude = position.coords.latitude;
        longitude = position.coords.longitude
    });
	//This creates a new form and inserts it into the body
	//Register this listener so that new entities will be created on button click
	new ModalNamer().$el.modal('show');
});