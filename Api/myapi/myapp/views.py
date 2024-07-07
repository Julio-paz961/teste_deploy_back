from http.client import HTTPException
from dotenv import load_dotenv
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import Message
from .serializers import MessageSerializer
from openai import OpenAI
import uuid
import os

load_dotenv()
# Acessando a variável de ambiente API_KEY

client = OpenAI(api_key=os.getenv("API_KEY"))

# Funções definidas anteriormente para a interação com o assistente
function = [{"type": "function",
             "function": {"name": "get_name",
                          "description": "This function is designed to get the client's name at the outset of a conversation, ensuring personalized interaction and communication.",
                          "parameters": {"type": "object",
                                         "properties": {"name": {"type": "string",
                                                                 "description": "The client's name."}},
                                         "required": ["name"]}}},
            {"type": "function",
             "function": {"name": "get_machine_type",
                          "description": "This function is designed to get basic information about the client's desired machine, ensuring personalized interaction and communication.",
                          "parameters": {"type": "object",
                                         "properties": {"machine": {"type": "string",
                                                                    "description": "The options available are: 'loader', 'articulated hauler', 'rigid hauler', 'excavator' or 'unsure'."}},
                                         "required": ["machine"]}}},
            {"type": "function",
             "function": {"name": "get_application_info",
                          "description": "This function is designed to gather primary information about how the machine will be employed by the client. It aims to understand the specific industry segment and the type of activities the machine will perform. Make sure the client answer ALL of the questions before moving on.",
                          "parameters": {"type": "object",
                                         "properties": {"segment": {"type": "string",
                                                                    "description": "The industry segment where the machine will be used."},
                                                        "activity": {"type": "string",
                                                                     "description": "The specific activity that the machine will be performing within the chosen segment."}},
                                         "required": ["segment", "activity"]}}},
            {"type": "function",
             "function": {"name": "get_material_info",
                          "description": "This function is designed to gather detailed information about the materials that the client's machine will handle. Understanding the type, density, and condition of the material ensures that the machine recommended is capable of efficiently and effectively managing the materials involved. Make sure the client answer ALL of the questions before moving on.",
                          "parameters": {"type": "object",
                                         "properties": {"material": {"type": "string",
                                                                     "description": "The kind of material that will be transported by the client's machine, such as sand, gravel, rocks, etc."},
                                                        "condition": {"type": "string",
                                                                      "description": "The client must answer either 'loose' or 'in situ'. 'Loose' refers to material that is already broken up and can be easily loaded or moved, while 'in situ' refers to material that is in its original place and may require breaking or loosening."},
                                                        "density": {"type": "string",
                                                                    "description": "The density of the material, typically measured in kilograms per cubic meter (kg/m³) or pounds per cubic foot (lb/ft³). If the client is unsure, provide typical densities based on the chosen material and its condition."}},
                                         "required": ["material", "condition", "density"]}}},
            {"type": "function",
             "function": {"name": "get_environment_info",
                          "description": "This function is designed to progressively gather detailed information about the client's operational environment over multiple interactions. The collected data includes location, type of area and operational time of the year. Make sure the client answer ALL of the questions before moving on.",
                          "parameters": {"type": "object",
                                         "properties": {"location": {"type": "string",
                                                                     "description": "The city and state, e.g., San Francisco, CA. If only the city name is provided, please infer the State and then confirm with the client."},
                                                        "area": {"type": "string",
                                                                 "description": "The client must answer either 'urban' or 'rural'."},
                                                        "time": {"type": "string",
                                                                 "description": "The time of the year the machine will operate."}},
                                         "required": ["location", "area", "time"]}}},
            {"type": "function",
             "function": {"name": "get_extra_environment_info",
                          "description": "This function collects extra information about the operational environment when the client desires a 'loader', a 'hauler' or is 'unsure' about it's needs. The collected data includes the distance the machine will travel and the road conditions. Make sure the client answer ALL of the questions before moving on.",
                          "parameters": {"type": "object",
                                         "properties": {"distance": {"type": "string",
                                                                     "description": "The distance the machine will travel during its operations. The client must answer either 'more than 200m' or 'less than 200m'. This helps in understanding the operational range and potential wear and tear on the machine."},
                                                        "road": {"type": "string",
                                                                 "description": "The ground conditions on the work site, including appearance, gradients, surface quality, and other factors influencing the cycle time."}},
                                         "required": ["distance", "road"]}}},
            {"type": "function",
             "function": {"name": "get_specific_info",
                          "description": "This function asks additional questions to collect detailed information about other relevant aspects necessary to enhance the recommendation. Make sure the client gives some additional information before moving on to the recommendation",
                          "parameters": {"type": "object",
                                         "properties": {"info": {"type": "string",
                                                                 "description": "Extra information that is crucial for fine-tuning the machinery configuration. This information should be obtained by asking the client additional questions. DO NOT ask about the budget."}},
                                         "required": ["info"]}}},
            {"type": "function",
             "function": {"name": "get_recommendation",
                          "description": "This function creates a personalized and specific recommendation of Volvo machinery model for the client based on the data collected before.",
                          "parameters": {"type": "object",
                                         "properties": {"information": {"type": "string",
                                                                        "description": "All of the data collected by the function 'get_machine_type', 'get_application_info', 'get_material_info', 'get_environment_info', 'get_extra_environment_info' (depending on the case) and 'get_specific_info'."}},
                                         "required": ["information"]}}},
            {"type": "function",
             "function": {"name": "get_image",
                          "description": "This function retrieves a description of an image located at a provided URL.",
                          "parameters": {"type": "object",
                                         "properties": {"vision": {"type": "string",
                                                                   "description": "The image description that must be retrieved to the client."}},
                                         "required": ["vision"]}}}]

# Criar Assistente com funções definidas
assistant = client.beta.assistants.create(name="Volvo AI Assistant",
                                          instructions="You are an AI Volvo guidance system responsible for collecting the client's information and answering all of their questions in the process. You should reply to any message kindly and personal-like. Use the provided functions to ask the right questions. After asking the right questions, see if the client has any doubt.",
                                          model="gpt-4-turbo",
                                          tools=function)
# Criar uma Thread para armazenar o histórico de mensagens
thread = client.beta.threads.create()

class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer

    def create(self, request, *args, **kwargs):
        user_message = request.data.get('mensagem')
        new_post = Message(id=str(uuid.uuid4()), mensagem=user_message)
        new_post.save()

        # Adicionando mensagem a uma Thread
        message = client.beta.threads.messages.create(thread_id=thread.id, role="user", content=user_message)

        # Executando o Assistente na Thread
        run = client.beta.threads.runs.create_and_poll(thread_id=thread.id, assistant_id=assistant.id)

        # Processando a execução e manipulando ações necessárias
        if run.status != 'completed':
            while run.status == "requires_action":
                tool_outputs = []
                for tool in run.required_action.submit_tool_outputs.tool_calls:
                    if tool.function.name == "get_name":
                        tool_outputs.append({"tool_call_id": tool.id,
                                                "output": tool.function.arguments})
                    elif tool.function.name == "get_machine_type":
                        tool_outputs.append({"tool_call_id": tool.id,
                                                "output": tool.function.arguments})
                    elif tool.function.name == "get_application_info":
                        tool_outputs.append({"tool_call_id": tool.id,
                                                "output": tool.function.arguments})
                    elif tool.function.name == "get_material_info":
                        tool_outputs.append({"tool_call_id": tool.id,
                                                "output": tool.function.arguments})
                    elif tool.function.name == "get_environment_info":
                        tool_outputs.append({"tool_call_id": tool.id,
                                                "output": tool.function.arguments})
                    elif tool.function.name == "get_extra_environment_info":
                        tool_outputs.append({"tool_call_id": tool.id,
                                                "output": tool.function.arguments})
                    elif tool.function.name == "get_specific_info":
                        tool_outputs.append({"tool_call_id": tool.id,
                                                "output": tool.function.arguments})
                    elif tool.function.name == "get_recommendation":
                        tool_outputs.append({"tool_call_id": tool.id,
                                                "output": tool.function.arguments})
                    elif tool.function.name == "get_image":
                        vision = (OpenAI().chat.completions.create(model="gpt-4-vision-preview",
                                                                    messages=[{"role":"user","content":[{"type":"text", "text":"Describe what you see in the image, and don't forget that you are an AI Volvo guidance meant to help the user understand the usage cases of Volvo machinery."}, {"type":"image_url", "image_url":user_message}]}],
                                                                    max_tokens=300)).choices[0].message.content
                        tool_outputs.append({"tool_call_id": tool.id,
                                                "output": vision})
                
                if tool_outputs:
                    try:
                        run = client.beta.threads.runs.submit_tool_outputs_and_poll(thread_id=thread.id,
                                                                                    run_id=run.id,
                                                                                    tool_outputs=tool_outputs)
                        print("***** 2 - Run status:", run.status, "// Tool outputs submitted successfully! // tool_outputs:", tool_outputs, "// Function called:", tool.function.name)
                    except Exception as e:
                        print("***** Failed to submit tool outputs:", e)
                    else:
                        print("***** 3 - Run status:", run.status, "// No tool outputs to submit!")
                        # Saving the Messages list into a variable:
                        messages = client.beta.threads.messages.list(thread_id=thread.id)
                        # Getting the reply:
                        reply = messages.data[0].content[0].text.value

        else:
          # Saving the Messages list into a variable:
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            # Getting the reply:
            reply = messages.data[0].content[0].text.value

        resposta = Message(id=str(uuid.uuid4()), mensagem=reply)
        resposta.save()
        return Response(MessageSerializer(resposta).data, status=status.HTTP_201_CREATED)

@api_view(['GET'])
def read_posts(request):
    posts = Message.objects.all()
    serializer = MessageSerializer(posts, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def read_post(request, post_id):
    try:
        post = Message.objects.get(id=post_id)
    except Message.DoesNotExist:
        raise HTTPException(status_code=404, detail="Post not found")
    serializer = MessageSerializer(post)
    return Response(serializer.data)
