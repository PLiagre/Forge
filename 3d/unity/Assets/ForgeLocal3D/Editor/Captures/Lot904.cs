using System;using System.Collections;using System.Collections.Generic;using System.Globalization;using System.IO;using System.Linq;using Forge.Pont;using UnityEngine;using UnityEngine.Rendering;using Object=UnityEngine.Object;
namespace ForgeLocal3D.Captures
{
    // Lot 904 : Biskra murée en chantier, service en pause. Le départ au Zab, un tick, la route et l'enceinte carrée de ±80 m, deux ticks :
    // la ville de 1400 s'ouvre, et les témoins de capture tracent le contour lu de l'enceinte et un poteau à chaque porte.
    // Sous -forge904SansEnceinte, la route seule : la ville s'ouvre aussi, sans mur, sans porte ni témoin.
    static class Lot904
    {
        static Exception Faux(string m)=>new InvalidOperationException(m);static string N(double v)=>v.ToString("R",CultureInfo.InvariantCulture);static string P(PointLocal p)=>"["+N(p.X)+","+N(p.Y)+"]";
        static string Q(string s)=>"\""+(s??"").Replace("\\","\\\\").Replace("\"","\\\"").Replace("\n","\\n")+"\"";
        [ScenarioDeCapture(904,"biskra-muree")]
        static IEnumerator BiskraMuree(Camera camera)
        {
            bool sans=Environment.GetCommandLineArgs().Contains("-forge904SansEnceinte");string rapport=Path.Combine(Capture.DossierDesCaptures,"lot904-rapport.json");if(File.Exists(rapport))throw Faux("rapport antérieur : "+rapport);
            var outil=Object.FindFirstObjectByType<DesertRoadTool>()??throw Faux("pas d'outil");var ville=camera.GetComponent<DesertCityCamera>()??throw Faux("pas de caméra de ville");
            var lieu=Object.FindFirstObjectByType<PanneauLieu>()??throw Faux("pas de panneau du lieu");outil.automatique=ville.automatique=true;if(ville.Marcheur)ville.Marcheur.automatic=true;
            var lus=System.Threading.Tasks.Task.Run(()=>{using(var d=new ClientDeparts(outil.Port,ClientDeparts.DelaiMinimal))return d.Lire();});while(!lus.IsCompleted)yield return null;
            if(lus.IsFaulted||!lus.Result.Presente)throw Faux(lus.IsFaulted?lus.Exception.GetBaseException().Message:lus.Result.Absence);
            var zab=lus.Result.Donnees.Fiches.Where(f=>f.Siege.Nom=="Biskra").ToArray();if(zab.Length!=1)throw Faux(zab.Length+" sièges Biskra");long cellule=zab[0].CellId;string geste="\"maison\":\"seigneurie-"+zab[0].Id+"\",\"cell\":"+cellule;
            Lot362.Deposer(outil.Port,"{\"type\":\"choisir_depart\",\"seigneurie\":"+zab[0].Id+"}");Lot362.Tick(outil.Port);
            Lot362.Deposer(outil.Port,"{\"type\":\"tracer_route\","+geste+",\"points\":[[-66,2.2],[-120,2.2]],\"largeur_m\":4}");
            if(!sans)Lot362.Deposer(outil.Port,"{\"type\":\"tracer_enceinte\","+geste+",\"points\":[[-80,-80],[80,-80],[80,80],[-80,80]],\"foyers\":2}");
            Lot362.Tick(outil.Port);Lot362.Tick(outil.Port);
            var plan=Lot362.Lire(outil.Port,cellule);var natures=plan.ChantiersDuJour?.Select(c=>c.Nature).ToArray()??throw Faux("relevé absent : "+plan.AbsenceDesChantiersDuJour);
            bool mur=plan.Enceinte!=null&&plan.Enceinte.EnChantier,porte=plan.Portes.Any(p=>p.Point.X==-80&&p.Point.Y==2.2),ligne=natures.Contains("enceinte");
            if(sans?(plan.Enceinte!=null||plan.Portes.Count>0||ligne):!(mur&&porte&&ligne))throw Faux("plan du tick "+plan.Tick+" : enceinte en chantier "+mur+", porte à (-80, 2.2) "+porte+", relevé "+string.Join(",",natures));
            if(!outil.Ouvrir(cellule))throw Faux("ouverture : "+outil.Message);lieu.Ouvrir(cellule);
            if(outil.Maisons.Posees!=33||outil.Rues1400.Dessinees!=7)throw Faux(outil.Maisons.Posees+" maisons posées, "+outil.Rues1400.Dessinees+" rues de 1400 dessinées");
            var t=outil.roads.terrain;var coins=new[]{(-80.0,-80.0),(80.0,-80.0),(80.0,80.0),(-80.0,80.0),(-80.0,2.2)}.Select(c=>Lot362.Monde(t,c.Item1,c.Item2)).ToArray();
            if(!sans)
            {
                var defaut=GraphicsSettings.currentRenderPipeline?GraphicsSettings.currentRenderPipeline.defaultMaterial:null;if(!defaut)throw Faux("pas de matériau par défaut du pipeline");
                var temoin=new GameObject("Témoin 904 : enceinte lue");var trait=temoin.AddComponent<LineRenderer>();trait.loop=true;trait.widthMultiplier=1.5f;trait.material=new Material(defaut){color=new Color(.75f,.1f,.1f)};
                // Un sommet tous les 2 m, chacun à 1 m au-dessus du sol : un trait tendu d'un coin à l'autre passerait sous les dunes.
                var c=plan.Enceinte.Contour;var sommets=new List<Vector3>();
                for(int i=0;i<c.Count;i++){PointLocal a=c[i],b=c[(i+1)%c.Count];int n=Math.Max(1,(int)Math.Ceiling(Math.Sqrt((b.X-a.X)*(b.X-a.X)+(b.Y-a.Y)*(b.Y-a.Y))/2));for(int k=0;k<n;k++)sommets.Add(Lot362.Monde(t,a.X+(b.X-a.X)*k/n,a.Y+(b.Y-a.Y)*k/n)+Vector3.up);}
                trait.positionCount=sommets.Count;trait.SetPositions(sommets.ToArray());var bleu=new Material(defaut){color=new Color(.1f,.2f,.8f)};
                foreach(var p in plan.Portes){var poteau=GameObject.CreatePrimitive(PrimitiveType.Cylinder);poteau.name="Témoin 904 : porte";poteau.transform.SetParent(temoin.transform);poteau.transform.localScale=new Vector3(2f,3f,2f);poteau.transform.position=Lot362.Monde(t,p.Point.X,p.Point.Y)+Vector3.up*3f;poteau.GetComponent<Renderer>().sharedMaterial=bleu;}
            }
            // Surplomb à 65° : la caméra recule jusqu'à tenir les quatre coins du carré et la porte entre 0,02 et 0,98 de l'image.
            camera.aspect=1600f/900f;bool cadre=false;
            for(float d=60f;d<=DesertCityCamera.DistanceMax&&!cadre;d*=1.06f){ville.Poser(Lot362.Monde(t,0,0),ville.Cap,65f,d);cadre=coins.All(v=>{var q=camera.WorldToViewportPoint(v);return q.z>camera.nearClipPlane&&q.x>.02f&&q.x<.98f&&q.y>.02f&&q.y<.98f;});}
            if(!cadre)throw Faux("les coins de l'enceinte et la porte ne tiennent pas dans l'image");for(int i=0;i<10;i++)yield return null;
            var e=plan.Enceinte;string bilan="{\"cellule\":"+cellule+",\"tick\":"+plan.Tick+",\"enceinte\":"+(e==null?"null":"{\"contour\":["+string.Join(",",e.Contour.Select(P))+"],\"en_chantier\":"+(e.EnChantier?"true":"false")+",\"foyers\":"+e.Foyers+",\"travail_fourni\":"+e.TravailFourni+",\"travail_requis\":"+e.TravailRequis+"}")
                +",\"portes\":["+string.Join(",",plan.Portes.Select(p=>"{\"point\":"+P(p.Point)+",\"rue\":"+Q(p.Rue)+",\"identifiant\":"+p.Identifiant+",\"largeur_m\":"+N(p.LargeurM)+"}"))+"],\"natures\":["+string.Join(",",natures.Select(Q))+"]"
                +",\"maisons_posees\":"+outil.Maisons.Posees+",\"rues_dessinees\":"+outil.Rues1400.Dessinees+",\"message\":"+Q(outil.Message)+"}";
            File.WriteAllText(rapport,bilan);Debug.Log("CAPTURE_904 "+bilan);
        }
    }
}
