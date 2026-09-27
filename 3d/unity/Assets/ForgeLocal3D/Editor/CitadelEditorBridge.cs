using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;

namespace ForgeLocal3D
{
    // Reçoit uniquement les opérations de l'atelier (citadelle et désert) dans l'éditeur déjà
    // ouvert. Une scène sale ou une session Play de l'utilisateur reste intacte.
    [InitializeOnLoad]
    public static class CitadelEditorBridge
    {
        const string Folder="Library/ForgeCitadelle/";
        const string Active="Forge.Citadelle.Bridge.Active";
        const string Finished="Forge.Citadelle.Bridge.Finished";
        const string Setup="Forge.Citadelle.Bridge.Setup";
        const string RequestId="Forge.Citadelle.Bridge.Id";
        [Serializable] class Request { public string id,action; }
        [Serializable] class Response { public string id,status,message; public int code=-1; }
        [Serializable] class SceneData { public string path; public bool loaded,active; }
        [Serializable] class Scenes { public SceneData[] scenes; }
        static double next;
        static CitadelEditorBridge(){EditorApplication.update+=Tick;}
        static void Write(string status,string message,int code=-1)
        {
            Directory.CreateDirectory(Folder);
            var result=new Response{id=SessionState.GetString(RequestId,""),status=status,message=message,code=code};
            File.WriteAllText(Folder+"response.tmp",UnityEngine.JsonUtility.ToJson(result));
            File.Copy(Folder+"response.tmp",Folder+"response.json",true);
        }
        static void Restore()
        {
            try
            {
                var setup=UnityEngine.JsonUtility.FromJson<Scenes>(SessionState.GetString(Setup,""));
                if(setup?.scenes?.Length>0)EditorSceneManager.RestoreSceneManagerSetup(setup.scenes.Select(s=>new SceneSetup{path=s.path,isLoaded=s.loaded,isActive=s.active}).ToArray());
                int code=SessionState.GetInt(Finished,1);
                Write(code==0?"termine":"echec",code==0?"Opération terminée ; scènes ouvertes restaurées.":"Le contrôle a échoué ; consulter la console Unity.",code);
            }
            catch(Exception e){Write("echec",e.Message,1);UnityEngine.Debug.LogException(e);}
            finally{SessionState.SetBool(Active,false);SessionState.SetInt(Finished,-1);}
        }
        public static void Finish(int code)
        {
            UnityEngine.Time.captureFramerate=0;
            if(!SessionState.GetBool(Active,false)){EditorApplication.Exit(code);return;}
            SessionState.SetInt(Finished,code);
            if(EditorApplication.isPlaying)EditorApplication.ExitPlaymode();
        }
        static void Tick()
        {
            if(EditorApplication.timeSinceStartup<next)return;next=EditorApplication.timeSinceStartup+.5;
            if(EditorApplication.isCompiling||EditorApplication.isUpdating)return;
            if(SessionState.GetBool(Active,false))
            {
                if(SessionState.GetInt(Finished,-1)>=0&&!EditorApplication.isPlayingOrWillChangePlaymode)Restore();
                return;
            }
            if(!File.Exists(Folder+"request.json"))return;
            try
            {
                var request=UnityEngine.JsonUtility.FromJson<Request>(File.ReadAllText(Folder+"request.json"));
                SessionState.SetString(RequestId,request.id);
                if(EditorApplication.isPlayingOrWillChangePlaymode){Write("attente","Quitter le mode Play avant de lancer l'atelier.");return;}
                for(int i=0;i<EditorSceneManager.sceneCount;i++)
                {
                    var scene=EditorSceneManager.GetSceneAt(i);
                    if(scene.isDirty||string.IsNullOrEmpty(scene.path)){Write("attente","Enregistrer les scènes ouvertes avant de lancer l'atelier.");return;}
                }
                var known=new[]{"build","visite","parcours","joueur","batiments","desert_build","desert_visite","desert_parcours","desert_terrain"};
                if(!known.Contains(request.action))
                    throw new InvalidOperationException("Opération de l'atelier inconnue : "+request.action);
                SessionState.SetString(Setup,UnityEngine.JsonUtility.ToJson(new Scenes{scenes=EditorSceneManager.GetSceneManagerSetup().Select(s=>new SceneData{path=s.path,loaded=s.isLoaded,active=s.isActive}).ToArray()}));
                SessionState.SetBool(Active,true);SessionState.SetInt(Finished,-1);
                File.Delete(Folder+"request.json");Write("en_cours","Opération exécutée dans l'éditeur ouvert.");
                if(request.action=="build"){CitadelBuilder.Build();Finish(0);}
                else if(request.action=="joueur"){CitadelQuality.BuildPlayer();Finish(0);}
                else if(request.action=="batiments"){CitadelDecor.CaptureBuildings();Finish(0);}
                else if(request.action=="desert_build"){DesertBuilder.Build();Finish(0);}
                else if(request.action=="desert_terrain")DesertCityTerrain.Start();
                else if(request.action=="desert_visite")DesertPlayCheck.Start();
                else if(request.action=="desert_parcours")DesertTraversalCheck.Start();
                else if(request.action=="visite")CitadelPlayCheck.Start();
                else CitadelTraversalCheck.Start();
            }
            catch(Exception e)
            {
                UnityEngine.Debug.LogException(e);
                if(SessionState.GetBool(Active,false))Finish(1);
                else{File.Delete(Folder+"request.json");Write("echec",e.Message,1);}
            }
        }
    }
}
