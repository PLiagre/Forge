using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Threading.Tasks;
using Forge.Pont;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using Object=UnityEngine.Object;

namespace ForgeLocal3D
{
    // Contrôle du lot 361, en Play : Unity relancé redessine la même ville, à l'octet, d'après le seul
    // plan du monde. Trois sessions, chacune un lancement d'Unity sur la première implantation de la
    // sélection : `Tracer` (service neuf) trace deux routes par l'outil et en dépose une trop raide au
    // monde ; `Relancer` (même service) rouvre la ville et doit retrouver l'empreinte de `Tracer` ;
    // `Vierge` (service neuf) doit retrouver le sable vierge. Rien n'est capturé.
    // Lot 362 : les sessions portent aussi les parcelles du plan. `Tracer` en découpe deux sur la rue de
    // plaine (l'une s'achève, l'autre reste en chantier) ; `Relancer` doit les redessiner à la même
    // empreinte ; `Vierge` n'en dessine aucune.
    [InitializeOnLoad] public static class DesertCityRelance
    {
        const string Flag="Forge.Desert.Relance",Cle="Forge.Desert.Relance.Session",Id="Forge.Desert.Relance.Implantation";
        const string Output=DesertRoads.Sorties;
        const int DelaiTickS=60;
        static int last=-1,settle;

        [Serializable] class Selection{public string[] implantations;}
        [Serializable] public class Essai{public long identifiant=-1;public bool acceptee;public string motif="",message="";}
        [Serializable] public class Trace{public long identifiant=-1;public string etat="",message="";}
        [Serializable] public class Rapport
        {
            public string session="",implantation="";public long cell=-1;public int port=-1;public long tick_ouverture=-1;
            public Essai[] ouverture=new Essai[0],traces=new Essai[0];public long[] plan=new long[0];
            public string panneau="",empreinte="",vierge="";public string[] defauts=new string[0];
            public Trace[] parcelles_plan=new Trace[0],parcelles=new Trace[0];public int pieces_parcelles=-1;public string empreinte_parcelles="";
        }

        static DesertCityRelance(){EditorApplication.update+=Tick;}

        public static void Tracer()=>Lancer("tracer");
        public static void Relancer()=>Lancer("relance");
        public static void Vierge()=>Lancer("vierge");

        static void Lancer(string session)
        {
            var selection=JsonUtility.FromJson<Selection>(File.ReadAllText(Output+"selection.json"));
            if(selection?.implantations==null||selection.implantations.Length==0)
                throw new InvalidOperationException("Aucune implantation : lancer py local3d/atelier_desert.py relance");
            string id=selection.implantations[0];
            SessionState.SetString(Cle,session);SessionState.SetString(Id,id);
            EditorSceneManager.OpenScene(ScenePath(id));
            SessionState.SetBool(Flag,true);EditorApplication.EnterPlaymode();
        }
        static string ScenePath(string id)=>DesertBuilder.Root+"/Scenes/Forge_Desert_Ville_"+id+".unity";
        static string Chemin(string id,string session)=>Output+id+"/relance/"+session+".json";

        static void Tick()
        {
            if(!SessionState.GetBool(Flag,false)||!Application.isPlaying||last==Time.frameCount)return;last=Time.frameCount;
            // Deux images pour que les composants de la scène aient fait leur Awake et leur Start : l'outil a ouvert la ville.
            if(settle++<2)return;
            SessionState.SetBool(Flag,false);
            string session=SessionState.GetString(Cle,""),id=SessionState.GetString(Id,"");
            try
            {
                if(SceneManager.GetActiveScene().name!="Forge_Desert_Ville_"+id)
                    throw new InvalidOperationException("scène active "+SceneManager.GetActiveScene().name+" au lieu de Forge_Desert_Ville_"+id);
                var report=Run(session,id);
                Directory.CreateDirectory(Output+id+"/relance");
                File.WriteAllText(Chemin(id,session),JsonUtility.ToJson(report,true));
                Debug.Log("DESERT_RELANCE "+session+" "+id+" "+string.Join(" | ",report.defauts));
                CitadelEditorBridge.Finish(report.defauts.Length==0?0:1);
            }
            catch(Exception e){Debug.LogException(e);CitadelEditorBridge.Finish(1);}
        }

        static Vector3 World(Terrain t,double x,double y)
        {var p=new Vector3((float)-x,0,(float)-y);p.y=t.SampleHeight(p)+t.transform.position.y;return p;}
        static Essai Copie((long identifiant,DesertRoads.Resultat resultat) e)
            =>new Essai{identifiant=e.identifiant,acceptee=e.resultat.acceptee,motif=e.resultat.motif??"",message=e.resultat.message??""};
        static string Liste(IEnumerable<long> ids)=>"["+string.Join(", ",ids)+"]";

        // Un vrai tick, hors du fil de l'éditeur (comme Lot293.AuTick) : le service tourne à vitesse 0.
        static void Tick(int port,List<string> faults)
        {
            string url="http://127.0.0.1:"+port+"/tick?n=1";
            try
            {
                int statut=Task.Run(()=>
                {
                    using var http=new HttpClient{Timeout=TimeSpan.FromSeconds(DelaiTickS)};
                    using var corps=new ByteArrayContent(new byte[0]);
                    using var reponse=http.PostAsync(url,corps).GetAwaiter().GetResult();
                    return (int)reponse.StatusCode;
                }).GetAwaiter().GetResult();
                if(statut!=200)faults.Add("service : POST "+url+" rend le statut "+statut);
            }
            catch(Exception e){faults.Add("service : POST "+url+" a échoué ("+e.GetBaseException().Message+")");}
        }

        static Rapport Run(string session,string id)
        {
            var faults=new List<string>();
            var roads=Object.FindFirstObjectByType<DesertRoads>();var tool=Object.FindFirstObjectByType<DesertRoadTool>();
            if(!roads||!tool)throw new InvalidOperationException("Scène sans routes du joueur : relancer py local3d/atelier_desert.py terrain");
            var gestes=DesertRoads.Lire(id);
            tool.automatique=true;
            var report=new Rapport{session=session,implantation=id,cell=tool.Cellule,port=tool.Port,tick_ouverture=tool.TickOuverture,
                ouverture=tool.Ouverture.Select(Copie).ToArray()};
            if(session=="tracer")Tracer(tool,gestes,report,faults);
            using(var plan=new ClientPlan(tool.Port,TimeSpan.FromSeconds(1)))
            {
                var lu=plan.Lire(tool.Cellule);
                if(lu.Presente)report.plan=lu.Plan.Rues.Select(u=>u.Identifiant).ToArray();
                else faults.Add("service : "+lu.Absence);
                if(lu.Presente)report.parcelles_plan=lu.Plan.Parcelles.Select(p=>new Trace{identifiant=p.Identifiant,etat=p.EnChantier?"cordeau":"bornes"}).ToArray();
            }
            report.panneau=tool.Message;
            report.parcelles=tool.Parcelles.Select(p=>new Trace{identifiant=p.identifiant,etat=p.etat,message=p.message??""}).ToArray();
            report.pieces_parcelles=tool.RacineParcelles?tool.RacineParcelles.childCount:-1;report.empreinte_parcelles=tool.EmpreinteParcelles;
            report.empreinte=roads.Empreintes().Tout;
            roads.Preparer(gestes.parametres,gestes.graine);report.vierge=roads.Empreintes().Tout;
            roads.Restaurer();

            if(report.tick_ouverture<0)faults.Add("l'outil n'a pas lu de plan à l'ouverture (tick_ouverture -1) : "+report.panneau);
            if(session=="tracer")JugerTracer(report,faults);
            else
            {
                string chemin=Chemin(id,"tracer");
                if(!File.Exists(chemin))faults.Add("rapport de la session tracer absent : "+chemin);
                else
                {
                    var tracer=JsonUtility.FromJson<Rapport>(File.ReadAllText(chemin));
                    if(session=="relance")JugerRelance(report,tracer,faults);else JugerVierge(report,tracer,faults);
                }
            }
            report.defauts=faults.ToArray();
            return report;
        }

        // Service neuf : la route de plaine puis celle de flanc, cliquées à l'écran et tracées par le
        // monde ; puis la première route trop raide déposée directement, sans l'essai du relief.
        static void Tracer(DesertRoadTool tool,DesertRoads.Gestes gestes,Rapport report,List<string> faults)
        {
            var terrain=tool.roads.terrain;var camera=tool.view;var traces=new List<Essai>();
            foreach(var famille in new[]{"plaine","flanc"})
            {
                var g=gestes.routes.FirstOrDefault(x=>x.famille==famille);
                if(g==null){faults.Add("jeu de gestes sans route "+famille);continue;}
                // Vue de haut, assez haut pour que tous les points tiennent dans l'image.
                var centre=World(terrain,g.x.Average(),g.y.Average());
                double etendue=Enumerable.Range(0,g.x.Length).Max(i=>Math.Max(Math.Abs(g.x[i]-g.x.Average()),Math.Abs(g.y[i]-g.y.Average())));
                var rt=new RenderTexture(1600,900,24);camera.targetTexture=rt;
                camera.transform.position=centre+new Vector3(0,Mathf.Max(120,(float)(etendue*2.5)),-.5f);camera.transform.LookAt(centre);camera.fieldOfView=60;
                tool.largeur=g.largeur;tool.Annuler();bool clique=true;
                for(int i=0;i<g.x.Length;i++)clique&=tool.Clic(camera.WorldToScreenPoint(World(terrain,g.x[i],g.y[i])));
                var essai=clique?tool.Valider():null;camera.targetTexture=null;rt.Release();Object.DestroyImmediate(rt);
                if(!clique){faults.Add("route "+g.id+" ("+famille+") : un point n'a pas été cliqué sur le terrain");tool.Annuler();continue;}
                if(essai==null||!essai.acceptee){faults.Add("route "+g.id+" ("+famille+") refusée à l'essai : "+tool.Message);continue;}
                if(tool.Recu==null||!tool.Recu.Acceptee){faults.Add("route "+g.id+" ("+famille+") non acceptée par le monde : "+tool.Message);continue;}
                Tick(tool.Port,faults);
                if(!tool.Attendre()){faults.Add("route "+g.id+" ("+famille+") : après le tick, l'outil n'a pas relu de plan plus récent que son dépôt");continue;}
                traces.AddRange(tool.Posees.Select(Copie));
            }
            report.traces=traces.ToArray();
            // Lot 362 : deux parcelles sur la rue de plaine, segments 3 et 4, à gauche ; la première, à 100 foyers,
            // s'achève avant la seconde. Hors du fil de l'éditeur, comme le dépôt de la route raide.
            if(report.traces.Length==0)faults.Add("pas de rue de plaine tracée : aucune parcelle découpée");
            else
            {
                string decoupe="{\"type\":\"decouper_parcelle\",\"cell\":"+tool.Cellule.ToString(CultureInfo.InvariantCulture)+",\"rue\":"+report.traces[0].identifiant.ToString(CultureInfo.InvariantCulture);
                var decoupes=new[]{decoupe+",\"segment\":3,\"debut_m\":1,\"facade_m\":8,\"profondeur_m\":15,\"cote\":\"gauche\",\"foyers\":100}",decoupe+",\"segment\":4,\"debut_m\":1,\"facade_m\":8,\"profondeur_m\":15,\"cote\":\"gauche\"}"};
                int portParcelles=tool.Port;
                var recusParcelles=Task.Run(()=>{using var depot=new ClientIntention(portParcelles,TimeSpan.FromSeconds(5));return decoupes.Select(depot.Deposer).ToArray();}).GetAwaiter().GetResult();
                for(int i=0;i<recusParcelles.Length;i++)if(!recusParcelles[i].Acceptee)faults.Add("parcelle du segment "+(3+i)+" non acceptée par le monde : "+(recusParcelles[i].Presente?recusParcelles[i].Erreur:recusParcelles[i].Absence));
                Tick(portParcelles,faults);
            }

            var raide=gestes.routes.FirstOrDefault(x=>x.famille=="raide_long");
            if(raide==null){faults.Add("jeu de gestes sans route raide_long");return;}
            string intention=tool.Intention(raide);int port=tool.Port;
            var recu=Task.Run(()=>{using var depot=new ClientIntention(port,TimeSpan.FromSeconds(5));return depot.Deposer(intention);}).GetAwaiter().GetResult();
            if(!recu.Acceptee)faults.Add("route "+raide.id+" (raide_long) non acceptée par le monde : "+(recu.Presente?recu.Erreur:recu.Absence));
            Tick(port,faults);
            // Deux fois de suite : un dessin qui ne viderait pas la racine y laisserait 4 parcelles au lieu de 2.
            if(!tool.Rafraichir()||!tool.Rafraichir())faults.Add("l'outil n'a pas redessiné les parcelles du plan : "+tool.Message);
        }

        // Lot 362 : une liste de parcelles « id état », et l'égalité de deux listes (identifiants, états, ordre).
        static string Etats(IEnumerable<Trace> t)=>"["+string.Join(", ",t.Select(x=>x.identifiant+" "+x.etat))+"]";
        static bool Memes(Trace[] a,Trace[] b)=>a.Select(x=>(x.identifiant,x.etat)).SequenceEqual(b.Select(x=>(x.identifiant,x.etat)));

        static void JugerTracer(Rapport r,List<string> faults)
        {
            if(r.parcelles_plan.Length!=2||r.parcelles_plan[0].etat!="bornes"||r.parcelles_plan[1].etat!="cordeau")
                faults.Add("le plan n'a pas une parcelle achevée puis une en chantier : "+Etats(r.parcelles_plan));
            if(!Memes(r.parcelles,r.parcelles_plan))faults.Add("parcelles dessinées "+Etats(r.parcelles)+" différentes du plan "+Etats(r.parcelles_plan));
            foreach(var p in r.parcelles.Where(x=>x.etat=="refusee"))faults.Add("parcelle "+p.identifiant+" refusée : "+p.message);
            if(r.pieces_parcelles!=2)faults.Add(r.pieces_parcelles+" parcelle(s) sous la racine des parcelles au lieu de 2");
            if(r.ouverture.Length>0)faults.Add("le service n'est pas neuf : "+r.ouverture.Length+" rue(s) essayée(s) à l'ouverture");
            if(r.traces.Length!=2||!r.traces.All(t=>t.acceptee)||r.traces.Select(t=>t.identifiant).Distinct().Count()!=r.traces.Length)
                faults.Add("traces : "+r.traces.Length+" essai(s) "+Liste(r.traces.Select(t=>t.identifiant))+", il en faut exactement 2 acceptés, d'identifiants distincts");
            if(r.plan.Length!=3)faults.Add("le plan compte "+r.plan.Length+" rue(s) "+Liste(r.plan)+" au lieu de 3");
            if(r.empreinte==r.vierge)faults.Add("la ville tracée a l'empreinte du sable vierge");
        }

        static void JugerRelance(Rapport r,Rapport tracer,List<string> faults)
        {
            var essayes=r.ouverture.Select(e=>e.identifiant).ToArray();
            if(!essayes.SequenceEqual(r.plan))faults.Add("ouverture "+Liste(essayes)+" différente du plan "+Liste(r.plan)+" : une rue sautée ou essayée deux fois");
            var acceptes=r.ouverture.Where(e=>e.acceptee).Select(e=>e.identifiant).ToArray();var traces=tracer.traces.Select(t=>t.identifiant).ToArray();
            if(!acceptes.SequenceEqual(traces))faults.Add("rues posées à l'ouverture "+Liste(acceptes)+" différentes des traces de la session tracer "+Liste(traces));
            var refusees=r.ouverture.Where(e=>!e.acceptee).ToArray();
            if(refusees.Length!=1)faults.Add(refusees.Length+" rue(s) refusée(s) à l'ouverture au lieu de 1");
            var absente=r.plan.Where(i=>!traces.Contains(i)).ToArray();
            foreach(var e in refusees)
            {
                if(absente.Length!=1||absente[0]!=e.identifiant)faults.Add("rue "+e.identifiant+" refusée, alors que la rue du plan absente des traces est "+Liste(absente));
                if(string.IsNullOrEmpty(e.motif))faults.Add("rue "+e.identifiant+" refusée sans motif");
                if(!r.panneau.Contains("Rue "+e.identifiant+" refusée par le relief"))faults.Add("le panneau ne déclare pas la rue "+e.identifiant+" refusée : "+r.panneau);
            }
            if(r.empreinte!=tracer.empreinte)faults.Add("la ville relancée n'a pas l'empreinte de la ville tracée");
            if(r.vierge!=tracer.vierge)faults.Add("le sable vierge de cette session n'est pas celui de la session tracer");
            if(!Memes(r.parcelles,r.parcelles_plan)||!Memes(r.parcelles,tracer.parcelles))
                faults.Add("parcelles relancées "+Etats(r.parcelles)+" différentes du plan "+Etats(r.parcelles_plan)+" ou de la session tracer "+Etats(tracer.parcelles));
            if(r.pieces_parcelles!=2)faults.Add(r.pieces_parcelles+" parcelle(s) sous la racine des parcelles au lieu de 2");
            if(r.empreinte_parcelles!=tracer.empreinte_parcelles)faults.Add("les parcelles relancées n'ont pas l'empreinte de la session tracer");
        }

        static void JugerVierge(Rapport r,Rapport tracer,List<string> faults)
        {
            if(r.parcelles_plan.Length>0)faults.Add("le plan d'un service neuf compte "+r.parcelles_plan.Length+" parcelle(s) "+Etats(r.parcelles_plan));
            if(r.parcelles.Length>0||r.pieces_parcelles!=0)
                faults.Add(r.parcelles.Length+" parcelle(s) dessinée(s) contre un service vide "+Etats(r.parcelles)+", "+r.pieces_parcelles+" sous la racine des parcelles");
            if(r.plan.Length>0)faults.Add("le plan d'un service neuf compte "+r.plan.Length+" rue(s) "+Liste(r.plan));
            if(r.ouverture.Length>0)faults.Add(r.ouverture.Length+" rue(s) essayée(s) à l'ouverture "+Liste(r.ouverture.Select(e=>e.identifiant)));
            if(r.empreinte!=r.vierge)faults.Add("la ville n'est pas revenue vierge : son empreinte n'est pas celle du sable vierge");
            if(r.vierge!=tracer.vierge)faults.Add("le sable vierge de cette session n'est pas celui de la session tracer");
        }
    }
}
