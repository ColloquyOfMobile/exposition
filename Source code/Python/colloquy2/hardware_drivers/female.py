
def female():    
    return {
            "children":{
                "drives": {
                    "children":{
                        "O": drive(start_value=300),
                        "P": drive(start_value=1200),
                        },
                    },
                },
            }

def drive(start_value):
    return {
        "children":{
            "start value":{
                "value": start_value
            },
        },
    }