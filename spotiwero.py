#Librerias a utilizar
import requests
import re
from bs4 import BeautifulSoup
import spotipy
import spotipy.util as util
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy.oauth2 as oauth2
import pandas as pd
from pandas.io.json import json_normalize

#inicio de web scrapping
#creamos una lista vacia, es donde vamos a estar recibiendo los enlaces de las paginas que usaremos para el web scraping
#dentro de un while, reviso que exista la palabra https://open.spotify.com/user/
#si no aparece esa información, entonces termina el while
urls=[]
while True:
    entrada = input("Hola, introduce el link de tu enlace de perfil de spotify, puedes introducir cualquier otra cosa para salir")
    if 'https://open.spotify.com/user/' in entrada:
        urls.append(entrada)
    else:
        break
print("Por favor espera un poco estoy ejecutando")

#ejecuto el requests de cada una de las urls que ingresamos y lo guardo en una lista llamada html, 
#la cual es todo el codigo que se ejecuta en la construccion de la pagina web
#es importante aclarar que las paginas son creadas dinamicamente, por lo que este request, obtiene el codigo del script que difiere
#respecto del que en un principio se leyó
html =[requests.get(url).content for url in urls]
print("Haciendo el web scraping")
#ejecuto la expresion regular que me va a traer los usuarios de los enlaces de usuarios, esta busca el signos de ? y se trae cualquier elemento alfanumerico
#find all crea una lista, asi que por eso extraigo el elemento 0
usrs =[re.findall(r'\w*(?=\?)', url) for url in urls]
print("------------------------------------------")
print(usrs)
usuariosID = [elemento[0] for elemento in usrs]

#aqui estamos separando de todo el contenido de las html exclusivamente las playlist de la lista html
playlists = [re.findall(r'\/playlist\/\w*', str(pagina)) for pagina in html]
print("calma ve por una cerveza, estoy buscando los nombres de las playlist ")
#ejecuto beautifulSoup para todas las paginas que estan en la lista html
soups = [BeautifulSoup(pagina, 'lxml') for pagina in html]

#busco todas las etiquetas de span, que tengan en el atributo dir el valor auto, esto nos arroja 
#una lista con los nombres de las playlist y los nombres de usuario
az = [soup.find_all('span',{'dir':'auto'}) for soup in soups]

print("Ya casi")

#estas listas son en donde se van a guardar los nombres de las playlist y los de usuario, extrayendolos de la lista llamada az
PlstName=[]
nombres = []
for etiquetas in az:
    limpio =[]
    for contenido in etiquetas:
        #convierto a string y elimino las etiquetas de span
        limpio.append(str(contenido).replace('<span dir="auto">', '').replace('</span>', ''))
        #distingo el nombre de usuario, del nombre de la playlist
    nombres.append(limpio[0])
    PlstName.append(limpio[1:])
print("Nombre Playlist", PlstName)
print("nombres", nombres)

#Estas tres variables forman el nucleo final del webscraping
#en listota estoy guardando los diccionarios
listota = []
#el diccionario me separará los siguientes campos 'Id_usr', 'Nombre_perfil', 'PlaylistName','Id_playlist' que son las listas por separado
diccionario = {}
#comprimido hace tuplas de cada uno de los valores que recibe, en este caso uso listas en el orden que requiero para el diccionario
comprimido = zip(usuariosID, nombres, PlstName,playlists)

#Realizo la iteracion de cada elemento de comprimido (llamado rar) y despues la longitud del indice 2 (que son las playlist de los usuarios)
#y con ese campo que tiene la misma longitud de los nombres de las playlists formo el diccionario
for rar in comprimido:
    for p in range(len(rar[2])):
        diccionario= {'Id_usr':rar[0], 'Nombre_perfil':rar[1], 'PlaylistName':rar[2][p] ,'Id_playlist':rar[3][p]}
        #si no hago una copia del diccionario, siempre me va a agregar el mismo, por hacer la referencia al que se encuentra en la memoria
        listota.append(diccionario.copy())

#creamos el dataframe final, con los diccionarios de la listota
scrapdf = pd.DataFrame(listota)
#reinicio los indices solo para el caso de que se necesite mostrar el dataframe del webscrap
scrapdf.reset_index()

#guardamos resultados en un archivo .csv, elimnando la columna de index
scrapdf.to_csv("./output/UsrPlay.csv", index = False)

#Fin de Web scraping
#comienzo de API Parsing

#variables para poder conectar a la API de spotifi, son provistos por developer spotify
CLIENT_ID = "2b7f57a2e7d74e43b0a0771a99fbb470"
CLIENT_SECRET = "219cfd4ed31349d5b3175e3526de4921"

#Autentificacion y uso de las variables de arriba
credentials = oauth2.SpotifyClientCredentials(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET)

#Creacion de los token de autenticación de spotify
token = credentials.get_access_token()
spotify = spotipy.Spotify(auth=token)

#Creamos el diccionario base con el que comenzaremos a concatenar, esas llaves son las mismas que trae la api de spotify
apiDF = pd.DataFrame({'href':[], 'items':[], 'limit':[], 'next':[], 'offset':[], 'previous':[], 'total':[]})

#en esta lista, guardaremos los dataframes que resulten de la iteracion del metodo .user_playlist_tracks
dataframes = []

#usamos el id de usuario y el id de la playlist, que proviene del data frame del resultado anterior 
#para obtener las canciones y todos los datos que se manejan en la bd de spotify y lo guardo en una lista
for row in scrapdf.itertuples():
    canciones = spotify.user_playlist_tracks(row.Id_usr, str(row.Id_playlist).replace('/playlist/', ''))
    dataframes.append(pd.DataFrame(canciones))

#hacemos concat, para agregar todos los dataframes guardados en la lista a un data drafe mas grande
apiDF = pd.concat(dataframes)

#solo compruebo que se conservan los mismos nombres de las columnas del dataframe llamado apiDF
apiDF.columns
#reinicio los indices, para que sean continuos, si no se hiciera, no se mostraria el indice correcto
apiDF.reset_index()

#en candionero2, lo que hago es normalizar el json de la columna llamada items y a continuacion la imprimo solo para ver cuales son las columnas
#que se encuentran dentro de items
candionero2 = json_normalize(apiDF['items'])
candionero2.columns
#creo un dataframe conformado por las columnas de candionero2, con los campos que me sirven
dfinal = candionero2[['added_by.id','track.name', 'track.external_urls.spotify', 'track.popularity']]

#guardamos el dataframe en un csv
dfinal.to_csv("./output/SpotifyApi.csv", index = False)
