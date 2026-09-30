using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.SceneManagement;

namespace ForgeLocal3D
{
    // Caméra de la capitale (lot 251) : un point visé au sol, un cap, une inclinaison, une distance.
    // Poser est la seule entrée : le joueur, la touche F et le contrôle passent tous par elle. Elle
    // borne les quatre valeurs, garde la caméra au-dessus de l'emprise du terrain, puis applique la
    // garde : la caméra et les coins de son plan proche restent à Marge au moins au-dessus du
    // terrain vivant (la copie que les routes retaillent), lu à chaque pose. Tab descend marcher à
    // hauteur d'homme sous le point visé ; Tab encore rend la vue quittée. Aucun état du monde.
    public sealed class DesertCityCamera : MonoBehaviour
    {
        public const float DistanceMin=6,DistanceMax=450,InclinaisonMin=5,InclinaisonMax=85,InclinaisonEnsemble=40,Marge=1.1f,Bord=2;
        public DesertRoadTool outil;
        // Contre-épreuve seulement : sans garde, la caméra peut passer sous le terrain.
        public bool garde=true;
        // Piloté par le contrôle : ni souris ni clavier.
        public bool automatique;
        public Vector3 Vise{get;private set;}
        public float Cap{get;private set;}
        public float Inclinaison{get;private set;}
        public float Distance{get;private set;}
        public CitadelTraversal Marcheur{get;private set;}
        Terrain terrain;Camera view;Vector3 ensemble;float capEnsemble,champ;

        // Branchement sans réécrire les scènes : toute scène qui porte l'outil des routes reçoit la caméra.
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
        static void Brancher(){SceneManager.sceneLoaded-=Charger;SceneManager.sceneLoaded+=Charger;}
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Rattraper(){for(int i=0;i<SceneManager.sceneCount;i++)Charger(SceneManager.GetSceneAt(i),LoadSceneMode.Additive);}
        static void Charger(Scene scene,LoadSceneMode mode)
        {
            if(!scene.isLoaded)return;
            foreach(var racine in scene.GetRootGameObjects())
                foreach(var o in racine.GetComponentsInChildren<DesertRoadTool>(true))
                    if(o.view&&!o.view.GetComponent<DesertCityCamera>())o.view.gameObject.AddComponent<DesertCityCamera>().outil=o;
        }

        void Start()=>Initialiser();

        bool Initialiser()
        {
            if(Marcheur)return true;
            if(!outil||!outil.roads||!outil.roads.terrain)return false;
            terrain=outil.roads.terrain;view=GetComponent<Camera>();champ=view.fieldOfView;
            // DesertEnvironment (touche F) lit un VillageV2Visit sur la caméra : un exemplaire éteint lui évite une erreur.
            if(!GetComponent<VillageV2Visit>())gameObject.AddComponent<VillageV2Visit>().enabled=false;
            var body=new GameObject("Marcheur du joueur").AddComponent<CharacterController>();
            body.height=1.8f;body.radius=.3f;body.center=new Vector3(0,.9f,0);body.enabled=false;
            Marcheur=body.gameObject.AddComponent<CitadelTraversal>();
            Marcheur.body=body;Marcheur.view=view;Marcheur.routes=new CitadelTraversal.Route[0];Marcheur.plots=new CitadelTraversal.Plot[0];
            Marcheur.tabulation=false;Marcheur.automatic=automatique;
            // Au départ, la vue que la scène a posée : le point visé est là où elle regarde.
            var t=view.transform;var o=terrain.transform.position;var size=terrain.terrainData.size;
            ensemble=terrain.GetComponent<TerrainCollider>().Raycast(new Ray(t.position,t.forward),out var hit,10000)?hit.point:o+size/2;
            capEnsemble=t.eulerAngles.y;
            Poser(ensemble,capEnsemble,Mathf.DeltaAngle(0,t.eulerAngles.x),Vector3.Distance(t.position,ensemble));
            return true;
        }

        // Hauteur rendue du terrain vivant.
        float Sol(Vector3 p)=>terrain.SampleHeight(p)+terrain.transform.position.y;
        // Pour la garde : le plus haut des quatre sommets du carreau, au-dessus de toute surface du carreau.
        float SolHaut(Vector3 p)
        {
            var td=terrain.terrainData;var o=terrain.transform.position;int n=td.heightmapResolution;
            int i=Mathf.Clamp(Mathf.FloorToInt((p.x-o.x)/td.size.x*(n-1)),0,n-2),j=Mathf.Clamp(Mathf.FloorToInt((p.z-o.z)/td.size.z*(n-1)),0,n-2);
            return o.y+Mathf.Max(Mathf.Max(td.GetHeight(i,j),td.GetHeight(i+1,j)),Mathf.Max(td.GetHeight(i,j+1),td.GetHeight(i+1,j+1)));
        }

        public void Poser(Vector3 vise,float cap,float inclinaison,float distance)
        {
            if(!Initialiser())return;
            var o=terrain.transform.position;var size=terrain.terrainData.size;
            float x0=o.x+Bord,x1=o.x+size.x-Bord,z0=o.z+Bord,z1=o.z+size.z-Bord;
            vise.x=Mathf.Clamp(vise.x,x0,x1);vise.z=Mathf.Clamp(vise.z,z0,z1);vise.y=Sol(vise);
            Vise=vise;Cap=Mathf.Repeat(cap,360);Inclinaison=Mathf.Clamp(inclinaison,InclinaisonMin,InclinaisonMax);
            Distance=Mathf.Clamp(float.IsNaN(distance)?DistanceMax:distance,DistanceMin,DistanceMax);
            var rotation=Quaternion.Euler(Inclinaison,Cap,0);var arriere=rotation*Vector3.back;
            // Au-dessus de l'emprise du terrain : près du bord, la caméra se rapproche dans la même direction.
            float d=Distance;
            if(arriere.x>1e-6f)d=Mathf.Min(d,(x1-vise.x)/arriere.x);else if(arriere.x<-1e-6f)d=Mathf.Min(d,(x0-vise.x)/arriere.x);
            if(arriere.z>1e-6f)d=Mathf.Min(d,(z1-vise.z)/arriere.z);else if(arriere.z<-1e-6f)d=Mathf.Min(d,(z0-vise.z)/arriere.z);
            var position=vise+arriere*d;
            view.fieldOfView=champ;
            if(garde)
            {
                // Le centre et les quatre coins du plan proche : on relève la caméra du plus grand manque.
                float n=view.nearClipPlane,hh=n*Mathf.Tan(view.fieldOfView*Mathf.Deg2Rad/2),hw=hh*Mathf.Max(view.aspect,1);
                float manque=SolHaut(position)+Marge-position.y;
                for(int sx=-1;sx<=1;sx+=2)for(int sy=-1;sy<=1;sy+=2)
                {var c=position+rotation*new Vector3(sx*hw,sy*hh,n);manque=Mathf.Max(manque,SolHaut(c)+Marge-c.y);}
                if(manque>0)position.y+=manque;
            }
            view.transform.SetPositionAndRotation(position,rotation);
        }

        public void VueEnsemble(){Remonter();Poser(ensemble,capEnsemble,InclinaisonEnsemble,DistanceMax);}

        // Le marcheur au sol sous le point visé, tourné comme la caméra ; l'œil à 1,7 m (CitadelTraversal).
        public void Descendre()
        {
            if(!Initialiser()||Marcheur.walking)return;
            var sol=Vise;sol.y=Sol(sol);
            Marcheur.spawn=sol+Vector3.up*.05f;Marcheur.Enter();
            Marcheur.Face(sol+Quaternion.Euler(0,Cap,0)*Vector3.forward);
        }
        // CitadelTraversal.Leave rend la pose qu'il avait gardée en entrant : celle de l'orbite.
        public void Remonter(){if(Marcheur&&Marcheur.walking)Marcheur.Leave();}

        void LateUpdate()
        {
            if(automatique||!Initialiser())return;
            var k=Keyboard.current;var mouse=Mouse.current;
            if(k!=null&&k.fKey.wasPressedThisFrame){VueEnsemble();return;}
            if(k!=null&&k.tabKey.wasPressedThisFrame){if(Marcheur.walking)Remonter();else Descendre();}
            // Pendant la marche, l'orbite ne bouge plus.
            if(Marcheur.walking)return;
            var vise=Vise;float cap=Cap,inclinaison=Inclinaison,distance=Distance;
            var glisse=Vector3.zero;
            if(k!=null)
            {
                if(k.upArrowKey.isPressed||k.zKey.isPressed||k.wKey.isPressed)glisse.z++;
                if(k.downArrowKey.isPressed||k.sKey.isPressed)glisse.z--;
                if(k.leftArrowKey.isPressed||k.qKey.isPressed||k.aKey.isPressed)glisse.x--;
                if(k.rightArrowKey.isPressed||k.dKey.isPressed)glisse.x++;
            }
            vise+=Quaternion.Euler(0,cap,0)*glisse.normalized*distance*.6f*Time.unscaledDeltaTime;
            if(mouse!=null)
            {
                var delta=mouse.delta.ReadValue();
                if(mouse.middleButton.isPressed)vise+=Quaternion.Euler(0,cap,0)*new Vector3(-delta.x,0,-delta.y)*distance*.0015f;
                if(mouse.rightButton.isPressed){cap+=delta.x*.2f;inclinaison-=delta.y*.2f;}
                // 120 par cran sous Windows, 1 selon la version du paquet : le zoom suit la distance.
                float molette=mouse.scroll.ReadValue().y,crans=Mathf.Abs(molette)>=20?molette/120:molette;
                if(crans!=0)distance*=Mathf.Pow(.85f,crans);
            }
            Poser(vise,cap,inclinaison,distance);
        }
    }
}
