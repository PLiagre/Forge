using System;using System.Collections;using System.Linq;using Forge.Pont;using UnityEngine;using Object=UnityEngine.Object;
namespace ForgeLocal3D.Captures
{
    static class Lot737
    {
        static string Decrire(Transform r){var s="";for(int i=0;i<r.childCount;i++){var t=r.GetChild(i);s+=t.name+" "+t.position.ToString("F3")+" "+t.eulerAngles.y.ToString("F2")+" "+t.localScale.x.ToString("F4")+"\n";}return s;}
        [ScenarioDeCapture(737,"01-biskra-de-haut")]
        static IEnumerator DeHaut(Camera camera)
        {
            var outil=Object.FindFirstObjectByType<DesertRoadTool>()??throw new InvalidOperationException("pas d'outil");
            var ville=camera.GetComponent<DesertCityCamera>()??throw new InvalidOperationException("pas de caméra de ville");
            var lieu=Object.FindFirstObjectByType<PanneauLieu>()??throw new InvalidOperationException("pas de panneau du lieu");
            outil.automatique=ville.automatique=true;if(ville.Marcheur)ville.Marcheur.automatic=true;
            var lus=System.Threading.Tasks.Task.Run(()=>{using(var d=new ClientDeparts(outil.Port,ClientDeparts.DelaiMinimal))return d.Lire();});
            while(!lus.IsCompleted)yield return null;
            if(lus.IsFaulted||!lus.Result.Presente)throw new InvalidOperationException(lus.IsFaulted?lus.Exception.GetBaseException().Message:lus.Result.Absence);
            var zab=lus.Result.Donnees.Fiches.Where(f=>f.Siege.Nom=="Biskra").ToArray();if(zab.Length!=1)throw new InvalidOperationException(zab.Length+" sièges Biskra");
            long cellule=zab[0].CellId;if(!outil.Ouvrir(cellule))throw new InvalidOperationException(outil.Message);lieu.Ouvrir(cellule);
            var pose=MaisonsDeLaBase.Poser(Lot362.Lire(outil.Port,cellule).Base??throw new InvalidOperationException("base absente : "+outil.Message));
            var m=outil.Maisons;var kit=KitDesBatiments.Charger();
            if(pose.Cases.Count!=33||m.Foyers!=33||m.Posees!=33||m.Refus.Count!=0||m.Racine.childCount!=33)throw new InvalidOperationException(m.Posees+" posées, "+m.Foyers+" foyers, "+m.Refus.Count+" refus : "+outil.Message.Replace("\n"," | "));
            for(int i=0;i<33;i++)if(!m.Racine.GetChild(i).GetComponentsInChildren<MeshFilter>(true).Select(f=>f.sharedMesh).SequenceEqual(kit.Maison((pose.Cases[i].Maison+pose.Cases[i].Indice)%6).Prefab.GetComponentsInChildren<MeshFilter>(true).Select(f=>f.sharedMesh)))throw new InvalidOperationException("variante "+i);
            if(!outil.Message.Contains("33 posée(s)")||!outil.Message.Contains("33 foyer(s)"))throw new InvalidOperationException(outil.Message.Replace("\n"," | "));
            string desc=Decrire(m.Racine);int pieces=outil.RacineBatiments.childCount;string emp=outil.EmpreinteBatiments;int nb=outil.Batiments.Count;
            if(pieces!=outil.PiecesAvantMaisons||emp!=outil.EmpreinteAvantMaisons||pieces!=outil.Batiments.Count(b=>b.etat!="refusee"))throw new InvalidOperationException("bâtiments de geste "+pieces+" contre "+outil.PiecesAvantMaisons);
            if(!outil.Ouvrir(cellule)||Decrire(outil.Maisons.Racine)!=desc||outil.Maisons.Posees!=33||outil.EmpreinteBatiments!=emp||outil.RacineBatiments.childCount!=pieces||outil.Batiments.Count!=nb)throw new InvalidOperationException("seconde ouverture : "+outil.Maisons.Posees);
            camera.aspect=1600f/900f;const float incl=68f,cap=40f;var inv=Quaternion.Inverse(Quaternion.Euler(incl,cap,0));
            float tv=Mathf.Tan(camera.fieldOfView*.5f*Mathf.Deg2Rad),th=tv*camera.aspect,d=40f;
            foreach(Transform e in outil.Maisons.Racine){var q=inv*(e.position+Vector3.up*6f);d=Mathf.Max(d,Mathf.Abs(q.x)/(th*.7f)-q.z,q.y/(tv*.62f)-q.z,-q.y/(tv*.42f)-q.z);}
            ville.Poser(Vector3.zero,cap,incl,d);outil.Placer();for(int i=0;i<8;i++)yield return null;
        }
        [ScenarioDeCapture(737,"02-rue-a-hauteur-d-homme")]
        static IEnumerator Rue(Camera camera)
        {
            var outil=Object.FindFirstObjectByType<DesertRoadTool>()??throw new InvalidOperationException("pas d'outil");
            var ville=camera.GetComponent<DesertCityCamera>()??throw new InvalidOperationException("pas de caméra de ville");
            ville.automatique=true;if(ville.Marcheur)ville.Marcheur.automatic=true;var plan=Lot362.Lire(outil.Port,outil.Cellule);
            RueDeBase rue=null;float mieux=1e9f;Vector2 mil=default;
            foreach(var r in plan.Base.Rues){var a=r.Points[0];var b=r.Points[r.Points.Count-1];var m=new Vector2((float)((a.X+b.X)*.5),(float)((a.Y+b.Y)*.5));float dist=1e9f;
                foreach(var h in plan.Base.Maisons){float cx=0,cy=0;foreach(var p in h.Emprise){cx+=(float)p.X;cy+=(float)p.Y;}dist=Mathf.Min(dist,Vector2.Distance(m,new Vector2(cx/h.Emprise.Count,cy/h.Emprise.Count)));}
                if(dist>4f&&dist<mieux){mieux=dist;rue=r;mil=m;}}
            if(rue==null)throw new InvalidOperationException("aucune rue bordée de maisons");
            var p0=rue.Points[0];var p1=rue.Points[rue.Points.Count-1];
            bool vers0=p0.X*p0.X+p0.Y*p0.Y<=p1.X*p1.X+p1.Y*p1.Y;float dx=(float)(vers0?p1.X-p0.X:p0.X-p1.X),dy=(float)(vers0?p1.Y-p0.Y:p0.Y-p1.Y);ville.Poser(new Vector3(-mil.x,0,-mil.y),Mathf.Atan2(dx,dy)*Mathf.Rad2Deg,12f,14f);ville.Descendre();
            for(int i=0;i<6;i++)yield return null;outil.Placer();int vues=0;
            foreach(Transform e in outil.Maisons.Racine){var vp=camera.WorldToViewportPoint(e.position+Vector3.up*2f);if(vp.z>1f&&vp.x>.02f&&vp.x<.98f&&vp.y>.08f&&vp.y<.92f)vues++;
                foreach(var rendu in e.GetComponentsInChildren<Renderer>())if(rendu.bounds.Contains(camera.transform.position))throw new InvalidOperationException("caméra dans "+e.name);}
            if(vues<2)throw new InvalidOperationException(vues+" façade(s) dans le champ");for(int i=0;i<4;i++)yield return null;
        }
    }
}
