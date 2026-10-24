using System;using System.Collections;using System.Collections.Generic;using System.Linq;using Forge.Pont;using UnityEditor;using UnityEngine;using Object=UnityEngine.Object;
namespace ForgeLocal3D.Captures
{
    // Lot 780 : deux comptoirs temporaires montés pour la photo au bord de la ville de 1400, comptoir, auvent et contenants vides séparés
    // des denrées : « nourriture » (dattes et épices) et « bois » (rondins). EtalDuBourg les règle sur des témoins typés du contrat #778
    // (cellule de l'outil, tick 0, référence 100 kg, bois 60 kg) : nourriture 100, 50 puis 0 kg, faim locale 0, 0 puis 9 ticks.
    // Ce montage montre le composant, pas le branchement au service, réservé à la suite de #420.
    static class Lot780
    {
        const double Bois=60;static readonly float[] Hauteur={1f,.78f};static EtalDuBourg[] etals;static Renderer[] comptoirs;static DesertCityCamera ville;static Vector3 centre;static long cellule;
        static Exception Faux(string m)=>new InvalidOperationException(m);
        static Material M(string nom)=>AssetDatabase.LoadAssetAtPath<Material>("Assets/ForgeLocal3D/Desert/Materials/"+nom+".mat")??throw Faux("matériau "+nom+" absent du projet");
        static Renderer Bloc(PrimitiveType t,Transform parent,string nom,Vector3 pos,Vector3 taille,string matiere,float roulis=0)
        {var g=GameObject.CreatePrimitive(t);g.name=nom;g.transform.SetParent(parent,false);g.transform.localPosition=pos;g.transform.localEulerAngles=new Vector3(0,0,roulis);g.transform.localScale=taille;var r=g.GetComponent<Renderer>();r.sharedMaterial=M(matiere);return r;}
        // Une seule préparation pour les trois scénarios, sur le côté le plus plat de la ville ; la caméra, le terrain ou un matériau manquant, elle échoue.
        static void Monter(Camera camera)
        {
            if(etals!=null&&etals.All(e=>e))return;ville=camera.GetComponent<DesertCityCamera>()??throw Faux("pas de caméra de ville");var terrain=ville.outil&&ville.outil.roads?ville.outil.roads.terrain:null;
            if(!terrain)throw Faux("pas de terrain");ville.automatique=true;if(ville.Marcheur)ville.Marcheur.automatic=true;cellule=ville.outil.Cellule;
            var tr=ville.outil.Maisons?.Racine;if(!tr||tr.childCount==0)throw Faux("aucune maison de 1400 au bord de laquelle poser");
            var bo=new Bounds(tr.GetChild(0).position,Vector3.zero);foreach(Transform t in tr)bo.Encapsulate(t.position);
            float Sol(Vector3 p)=>terrain.SampleHeight(p)+terrain.transform.position.y;
            float Relief(Vector3 p){var h=Enumerable.Range(0,21).Select(i=>Sol(p+new Vector3((i%7-3)*1.2f,0,(i/7-1)*1.5f))).ToArray();return h.Max()-h.Min();}
            centre=new[]{new Vector3(bo.center.x,0,bo.max.z+10),new Vector3(bo.center.x,0,bo.min.z-10),new Vector3(bo.max.x+10,0,bo.center.z),new Vector3(bo.min.x-10,0,bo.center.z)}.OrderBy(Relief).First();
            var racine=new GameObject("Lot 780 : étals du bourg").transform;etals=new EtalDuBourg[2];comptoirs=new Renderer[2];
            for(int k=0;k<2;k++){
                var etal=new GameObject(k==0?"Étal nourriture":"Étal bois").transform;etal.SetParent(racine);var pos=centre+Vector3.right*(k*2-1)*1.9f;pos.y=Sol(pos);etal.position=pos;
                comptoirs[k]=Bloc(PrimitiveType.Cube,etal,"comptoir",new Vector3(0,.45f,0),new Vector3(2.6f,.9f,1.2f),"bois_sombre");
                // L'auvent haut, au fond, et ses deux poteaux : il n'ombre que l'arrière et ne cache pas les denrées.
                Bloc(PrimitiveType.Cube,etal,"auvent",new Vector3(0,2.5f,-.45f),new Vector3(2.8f,.05f,.8f),k==0?"tissu_garance":"tissu_indigo");
                for(int s=-1;s<=1;s+=2){Bloc(PrimitiveType.Cube,etal,"poteau",new Vector3(s*1.25f,1.25f,-.8f),new Vector3(.08f,2.5f,.08f),"bois_palmier");Bloc(PrimitiveType.Cylinder,etal,"contenant vide",new Vector3(s*1.12f,.98f,.35f),new Vector3(.3f,.08f,.3f),"poterie");}
                var g=new GameObject("garniture").transform;g.SetParent(etal,false);g.localPosition=new Vector3(0,.9f,0);
                if(k==0)for(int i=0;i<3;i++)Bloc(PrimitiveType.Cube,g,"denrée",new Vector3((i-1)*.6f,.5f,0),new Vector3(.55f,1f,.9f),new[]{"dattes","epices_rouge","epices_jaune"}[i]);
                else foreach(var p in new[]{new Vector3(0,.2f,-.21f),new Vector3(0,.2f,.21f),new Vector3(0,.58f,0)})Bloc(PrimitiveType.Cylinder,g,"rondin",p,new Vector3(.4f,.9f,.4f),"bois_palmier",90);
                etals[k]=etal.gameObject.AddComponent<EtalDuBourg>();etals[k].Configurer(cellule,k==0?"nourriture":"bois",100,g);}
        }
        static IEnumerator Photo(Camera camera,double kg,long faim)
        {
            Monter(camera);var plan=LecturePlan.De(new PlanLu(cellule,0,new RueDuPlan[0],new ParcelleDuPlan[0],new BatimentDuPlan[0]));
            var bourg=Lecture<BourgLu>.De(new BourgLu(cellule,0,new DateDuMonde(1400,1),0,40,new Dictionary<string,double>{["nourriture"]=kg,["bois"]=Bois},faim,0));
            foreach(var e in etals)if(!e.Appliquer(bourg,plan))throw Faux(e.name+" : "+e.Cause);
            camera.aspect=1600f/900f;ville.Poser(centre+new Vector3(2f,0,-1f),180f,42f,11f);/* les étals à droite du panneau d'information */for(int i=0;i<30;i++)yield return null;Physics.SyncTransforms();
            // Comptoirs et garnitures dans le champ, la garniture à la hauteur du stock et vue sans obstacle ; au zéro, plus aucun rendu.
            bool Dans(Vector3 p){var v=camera.WorldToViewportPoint(p);return v.z>0f&&v.x>.02f&&v.x<.98f&&v.y>.02f&&v.y<.98f;}
            if(Object.FindObjectsByType<EtalDuBourg>(FindObjectsSortMode.None).Length!=2)throw Faux("deux étals témoins attendus");var bilan=new List<string>();
            for(int k=0;k<2;k++){
                var e=etals[k];var g=e.Garniture;var rs=g.GetComponentsInChildren<Renderer>(true);double rapport=Math.Min(1,(k==0?kg:Bois)/100);var c=comptoirs[k].bounds;
                if(!comptoirs[k].enabled||!Dans(c.min)||!Dans(c.max))throw Faux(e.name+" : comptoir caché ou hors du champ");
                if(rapport==0){if(rs.Any(r=>r.enabled))throw Faux(e.name+" : stock encore visible au zéro");bilan.Add(e.name+" vide");continue;}
                var b=rs.Select(r=>r.bounds).Aggregate((a,x)=>{a.Encapsulate(x);return a;});float h=b.max.y-g.position.y;var haut=new Vector3(b.center.x,b.max.y-.02f,b.center.z);
                bool vue=Physics.Raycast(camera.transform.position,haut-camera.transform.position,out var touche,100f)&&touche.transform.IsChildOf(g);
                if(rs.Any(r=>!r.enabled)||!Dans(b.min)||!Dans(b.max)||!vue||Mathf.Abs(h-Hauteur[k]*(float)rapport)>.01f)
                    throw Faux(e.name+" : garniture "+h.ToString("F3")+" m pour "+(Hauteur[k]*rapport).ToString("F3")+", vue "+vue+(touche.transform?" ("+touche.transform.name+")":""));
                bilan.Add(e.name+" "+(k==0?kg:Bois)+" kg, hauteur "+h.ToString("F2")+" m en "+camera.WorldToViewportPoint(b.center).ToString("F2"));}
            Debug.Log("CAPTURE_780 nourriture "+kg+" kg, bois "+Bois+" kg, faim locale "+faim+" : "+string.Join(" ; ",bilan));
        }
        [ScenarioDeCapture(780,"01-etals-pleins")]static IEnumerator Pleins(Camera camera)=>Photo(camera,100,0);
        [ScenarioDeCapture(780,"02-demi-stock")]static IEnumerator DemiStock(Camera camera)=>Photo(camera,50,0);
        [ScenarioDeCapture(780,"03-bourg-affame")]static IEnumerator Affame(Camera camera)=>Photo(camera,0,9);
    }
}
