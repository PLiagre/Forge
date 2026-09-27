using UnityEngine;

namespace Victoria.CityMode
{
    [CreateAssetMenu(menuName = "Victoria/City Visual Library", fileName = "CityLabVisualLibrary")]
    public sealed class CityVisualLibrary : ScriptableObject
    {
        public GameObject townCentrePrefab;
        public GameObject stockpilePrefab;
        public GameObject lumberCampPrefab;
        public GameObject[] lumberCampPrefabs;
        public GameObject[] housePrefabs;
        public GameObject[] granaryPrefabs;
        public GameObject[] warehousePrefabs;
        public GameObject[] marketPrefabs;
        public GameObject[] blacksmithPrefabs;
        public GameObject[] barnPrefabs;
        public GameObject[] chapelPrefabs;
        public GameObject villagerPrefab;
        public GameObject[] villagerPrefabs;
        public RuntimeAnimatorController villagerAnimatorController;
        public GameObject[] treePrefabs;
        public GameObject[] bushPrefabs;
        public GameObject[] rockPrefabs;
        public GameObject[] grassPrefabs;
        public GameObject[] propPrefabs;

        public bool HasDurableSlice => townCentrePrefab != null && stockpilePrefab != null &&
            housePrefabs != null && housePrefabs.Length > 0 &&
            (villagerPrefab != null || (villagerPrefabs != null && villagerPrefabs.Length > 0));

        public GameObject SelectBuildingPrefab(string visualFamily, int stableId)
        {
            var prefabs = visualFamily switch
            {
                "lumber_camp" => lumberCampPrefabs,
                "residence" => housePrefabs,
                "granary" => granaryPrefabs,
                "warehouse" => warehousePrefabs,
                "market" => marketPrefabs,
                "blacksmith" => blacksmithPrefabs,
                "barn" => barnPrefabs,
                "chapel" => chapelPrefabs,
                _ => null
            };
            if (prefabs == null || prefabs.Length == 0)
                return null;
            var available = 0;
            foreach (var prefab in prefabs)
                if (prefab != null)
                    available++;
            if (available == 0)
                return null;
            var selected = (stableId & int.MaxValue) % available;
            foreach (var prefab in prefabs)
            {
                if (prefab == null)
                    continue;
                if (selected-- == 0)
                    return prefab;
            }
            return null;
        }
    }

    public sealed class VillagerVisual : MonoBehaviour
    {
        Animator animator;
        Vector3 targetPosition;
        VillagerActivity activity;
        int carryingWood;
        GameObject carriedWood;
        static Material carriedWoodMaterial;

        public void Initialize(RuntimeAnimatorController controller)
        {
            animator = GetComponentInChildren<Animator>();
            if (animator != null && controller != null)
            {
                animator.runtimeAnimatorController = controller;
                animator.applyRootMotion = false;
            }
            CreateCarriedWood();
            targetPosition = transform.position;
        }

        void CreateCarriedWood()
        {
            carriedWood = new GameObject("Carried wood bundle");
            carriedWood.transform.SetParent(transform, false);
            carriedWood.transform.localPosition = new Vector3(0.35f, 0.88f, 0.16f);
            if (carriedWoodMaterial == null)
            {
                var source = Resources.Load<Material>("CityLabBaseMaterial");
                carriedWoodMaterial = new Material(source)
                {
                    name = "Runtime Carried Wood",
                    color = new Color(0.46f, 0.24f, 0.07f)
                };
            }
            for (var i = 0; i < 3; i++)
            {
                var log = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
                log.name = "Log";
                log.transform.SetParent(carriedWood.transform, false);
                log.transform.localPosition = new Vector3(0f, (i - 1) * 0.13f, 0f);
                log.transform.localRotation = Quaternion.Euler(0f, 0f, 90f);
                log.transform.localScale = new Vector3(0.075f, 0.28f, 0.075f);
                log.GetComponent<Renderer>().sharedMaterial = carriedWoodMaterial;
                var collider = log.GetComponent<Collider>();
                if (collider != null) collider.enabled = false;
            }
            carriedWood.SetActive(false);
        }

        public void Refresh(Vector3 position, VillagerActivity nextActivity, int nextCarryingWood)
        {
            targetPosition = position;
            activity = nextActivity;
            carryingWood = nextCarryingWood;
        }

        void Update()
        {
            var before = transform.position;
            transform.position = Vector3.Lerp(before, targetPosition, 1f - Mathf.Exp(-14f * Time.deltaTime));
            var delta = transform.position - before;
            var moving = delta.sqrMagnitude > 0.000001f;
            if (moving)
                transform.rotation = Quaternion.Slerp(transform.rotation,
                    Quaternion.LookRotation(delta.normalized, Vector3.up), 0.35f);

            if (animator != null)
            {
                animator.SetFloat("Speed", moving ? 1f : 0f);
                animator.SetBool("Working", activity == VillagerActivity.Building ||
                    activity == VillagerActivity.WorkingJob);
            }
            if (carriedWood != null)
                carriedWood.SetActive(carryingWood > 0);
        }
    }
}
