using System;using System.Collections;using System.Collections.Generic;using System.Linq;using Forge.Pont;using UnityEditor;using UnityEngine;using Object=UnityEngine.Object;
namespace ForgeLocal3D.Captures
{
    // Lot 779 : trois maisons du kit montées pour la photo (case de base habitée, maison bâtie occupée, maison bâtie vide), chacune avec sa
    // fumée et sa lampe, pilotées par EffetsDeMaison sur des témoins typés du contrat #778 (cellule de l'outil, tick 0, 12 kg de nourriture).
    // Ce n'est pas le branchement au service, réservé à la suite de #420. 01 à midi : deux fumées, aucune lampe ; 02 à 21 h : fumées et lampes.
    static class Lot779
    {
        static EffetsDeMaison[] maisons;static DesertCityCamera ville;static Vector3 centre;static long cellule;static Exception Faux(string m)=>new InvalidOperationException(m);
        // Une seule préparation pour les deux scénarios ; le kit, le matériau de fumée déjà au projet ou la caméra manquant, elle échoue.
        static void Monter(Camera camera)
        {
            if(maisons!=null)return;ville=camera.GetComponent<DesertCityCamera>()??throw Faux("pas de caméra de ville");var terrain=ville.outil&&ville.outil.roads?ville.outil.roads.terrain:null;
            var kit=KitDesBatiments.Charger();var fumee=AssetDatabase.LoadAssetAtPath<Material>("Assets/ForgeLocal3D/Desert/Materials/effet_fumee.mat");
            if(!terrain||!kit||!fumee)throw Faux("terrain "+(bool)terrain+", kit "+(bool)kit+", matériau de fumée "+(bool)fumee);
            ville.automatique=true;if(ville.Marcheur)ville.Marcheur.automatic=true;cellule=ville.outil.Cellule;
            // Au bord de la ville de 1400, du côté où le sol des maisons et de la caméra (+Z) est le plus plat.
            var tr=ville.outil.Maisons?.Racine;if(!tr||tr.childCount==0)throw Faux("aucune maison de 1400 au bord de laquelle poser");
            var bo=new Bounds(tr.GetChild(0).position,Vector3.zero);foreach(Transform t in tr)bo.Encapsulate(t.position);
            float Relief(Vector3 p){var h=Enumerable.Range(0,35).Select(i=>terrain.SampleHeight(p+new Vector3((i%7-3)*4f,0,(i/7-1)*5f))).ToArray();return h.Max()-h.Min();}
            centre=new[]{new Vector3(bo.center.x,0,bo.max.z+14),new Vector3(bo.center.x,0,bo.min.z-14),new Vector3(bo.max.x+16,0,bo.center.z),new Vector3(bo.min.x-16,0,bo.center.z)}.OrderBy(Relief).First();
            var racine=new GameObject("Lot 779 : maisons habitées").transform;maisons=new EffetsDeMaison[3];
            for(int k=0;k<3;k++){
                var piece=kit.Maison(k);if(!piece.Presente)throw Faux(piece.Absence);var pos=centre+new Vector3((k-1)*9f,0,0);pos.y=terrain.SampleHeight(pos)+terrain.transform.position.y;
                var m=Object.Instantiate(piece.Prefab,pos,Quaternion.identity,racine);m.name="Maison "+k;var b=m.GetComponentsInChildren<Renderer>().Select(r=>r.bounds).Aggregate((a,c)=>{a.Encapsulate(c);return a;});
                // La fumée au-dessus du toit, plus dense que celle du décor pour se lire de loin ; la lampe devant l'ouverture de la façade (+Z du prefab).
                var f=AlpineBuilder.Smoke(new float[3],fumee,m.transform,k);f.transform.position=new Vector3(b.center.x,b.max.y+.3f,b.center.z);
                var fm=f.main;fm.startSize=new ParticleSystem.MinMaxCurve(1.1f,1.8f);fm.startColor=new Color(.45f,.43f,.41f);fm.maxParticles=320;var fe=f.emission;fe.rateOverTime=40;
                var l=new GameObject("Lampe").AddComponent<Light>();l.transform.SetParent(m.transform);l.transform.position=new Vector3(b.center.x,b.min.y+1.8f,b.max.z+.9f);l.type=LightType.Point;l.color=new Color(1f,.62f,.28f);l.range=8f;l.intensity=5f;
                maisons[k]=m.AddComponent<EffetsDeMaison>();if(k==0)maisons[k].PourLaBase(f,l,cellule,1,2);else maisons[k].PourLeBatiment(f,l,cellule,9+k);}
        }
        static IEnumerator Photo(Camera camera,float heure)
        {
            Monter(camera);var env=Object.FindFirstObjectByType<DesertEnvironment>()??throw Faux("pas de DesertEnvironment");env.hour=heure;env.Apply();
            var c=new[]{new PointLocal(0,0),new PointLocal(6,0),new PointLocal(6,6)};var date=new DateDuMonde(1400,1);
            var plan=LecturePlan.De(new PlanLu(cellule,0,new RueDuPlan[0],new ParcelleDuPlan[0],new[]{new BatimentDuPlan(10,0,"maison",c,false,300,300),new BatimentDuPlan(11,0,"maison",c,false,300,300)},new BaseDuPlan(c,new RueDeBase[0],new[]{new MaisonDeBase(c,1),new MaisonDeBase(c,3)})));
            var bourg=Lecture<BourgLu>.De(new BourgLu(cellule,0,date,0,40,new Dictionary<string,double>{["nourriture"]=12,["bois"]=30},0,0));
            var occupation=Lecture<OccupationLue>.De(new OccupationLue(cellule,0,0,date,new[]{(0L,1L),(1L,3L)},new[]{(10L,4L,2L),(11L,3L,0L)},new Logement(7,2,0),null));
            foreach(var e in maisons)if(!e.Appliquer(bourg,occupation,plan,heure))throw Faux(e.name+" : "+e.Cause);
            camera.aspect=1600f/900f;ville.Poser(centre+Vector3.back*18f,180f,12f,50f);for(int i=0;i<30;i++)yield return null;
            // Les trois témoins et leurs effets dans le champ ; la vide sans rien, les habitées fument, leurs lampes n'éclairent que le soir.
            bool Dans(Vector3 p){var v=camera.WorldToViewportPoint(p);return v.z>0f&&v.x>.02f&&v.x<.98f&&v.y>.02f&&v.y<.98f;}
            string bilan=string.Join(", ",maisons.Select(e=>e.name+" "+e.Fumee.particleCount+" particule(s) en "+camera.WorldToViewportPoint(e.Fumee.transform.position).ToString("F2")+", lampe "+(e.Lampe.enabled?e.Lampe.intensity.ToString("F2"):"éteinte")));
            if(Object.FindObjectsByType<EffetsDeMaison>(FindObjectsSortMode.None).Length!=3||maisons.Any(e=>!Dans(e.transform.position+Vector3.up*2f)||!Dans(e.Fumee.transform.position)||!Dans(e.Lampe.transform.position)))throw Faux("témoins hors du champ : "+bilan);
            for(int k=0;k<3;k++){var e=maisons[k];bool habitee=k<2;if(e.Habitee!=habitee||(e.Fumee.particleCount>0)!=habitee||e.Lampe.enabled!=(habitee&&heure>=21f))throw Faux(bilan);}
            Debug.Log("CAPTURE_779 "+heure+" h : "+bilan);
        }
        [ScenarioDeCapture(779,"01-maisons-le-jour")]static IEnumerator LeJour(Camera camera)=>Photo(camera,12f);
        [ScenarioDeCapture(779,"02-maisons-le-soir")]static IEnumerator LeSoir(Camera camera)=>Photo(camera,21f);
    }
}
