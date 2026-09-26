Shader "Forge/AlpineLit"
{
    Properties
    {
        _BaseMap("Couleur",2D)="white"{}
        _BaseColor("Teinte",Color)=(1,1,1,1)
        _BumpMap("Normales",2D)="bump"{}
        _Smoothness("Lissage",Range(0,1))=.2
        _Cutoff("Découpe",Range(0,1))=.35
        _AlphaClip("Découper",Float)=0
        _Wind("Vent",Float)=0
        _SnowFactor("Neige",Float)=.4
        _EmissionColor("Fenêtres",Color)=(0,0,0,0)
        _Cull("Faces",Float)=0
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" "Queue"="Geometry" }
        Cull Off
        AlphaToMask On
        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
        TEXTURE2D(_BaseMap); SAMPLER(sampler_BaseMap);
        CBUFFER_START(UnityPerMaterial)
        float4 _BaseMap_ST,_BaseColor,_EmissionColor;
        float _Cutoff,_AlphaClip,_Wind,_SnowFactor,_Smoothness;
        CBUFFER_END
        float _AlpineWind,_AlpineSnow,_AlpineWet,_AlpineNight,_AlpineDaylight;
        float4 _AlpineAmbient;
        float3 _LightDirection;
        struct A { float4 vertex:POSITION;float3 normal:NORMAL;float2 uv:TEXCOORD0;UNITY_VERTEX_INPUT_INSTANCE_ID };
        struct V { float4 clip:SV_POSITION;float3 world:TEXCOORD0;float3 normal:TEXCOORD1;float2 uv:TEXCOORD2;float fog:TEXCOORD3;UNITY_VERTEX_INPUT_INSTANCE_ID };
        float3 Bend(float3 p)
        {
            float3 origin=TransformObjectToWorld(float3(0,0,0));
            float phase=origin.x*.075+origin.z*.08;
            float weight=pow(saturate(p.y/12),1.7);
            p.x+=sin(_Time.y*1.15+phase+p.y*.12)*weight*_Wind*_AlpineWind*.42;
            p.z+=cos(_Time.y*.82+phase)*weight*_Wind*_AlpineWind*.24;
            return p;
        }
        V Vert(A a)
        {
            V o;UNITY_SETUP_INSTANCE_ID(a);UNITY_TRANSFER_INSTANCE_ID(a,o);
            o.world=TransformObjectToWorld(Bend(a.vertex.xyz));o.clip=TransformWorldToHClip(o.world);
            o.normal=TransformObjectToWorldNormal(a.normal);o.uv=TRANSFORM_TEX(a.uv,_BaseMap);o.fog=ComputeFogFactor(o.clip.z);return o;
        }
        V ShadowVert(A a)
        {
            V o=Vert(a);
            o.clip=TransformWorldToHClip(ApplyShadowBias(o.world,normalize(o.normal),_LightDirection));
            #if UNITY_REVERSED_Z
            o.clip.z=min(o.clip.z,UNITY_NEAR_CLIP_VALUE);
            #else
            o.clip.z=max(o.clip.z,UNITY_NEAR_CLIP_VALUE);
            #endif
            return o;
        }
        half4 Frag(V i,bool front:SV_IsFrontFace):SV_Target
        {
            UNITY_SETUP_INSTANCE_ID(i);
            half4 tex=SAMPLE_TEXTURE2D(_BaseMap,sampler_BaseMap,i.uv)*_BaseColor;
            if(_AlphaClip>.5)clip(tex.a-_Cutoff);
            float3 normal=normalize(i.normal)*(front?1:-1);
            float snow=saturate(_AlpineSnow*_SnowFactor*pow(saturate(normal.y),2)*1.7);
            float3 color=lerp(tex.rgb*(1-_AlpineWet*.22),float3(.82,.88,.92),snow);
            Light light=GetMainLight(TransformWorldToShadowCoord(i.world));
            float ndl=saturate(dot(normal,light.direction))*.82+.12;
            float3 lit=color*(_AlpineAmbient.rgb+light.color*ndl*lerp(.30,1,light.shadowAttenuation));
            float3 view=normalize(GetWorldSpaceViewDir(i.world));float3 halfv=normalize(view+light.direction);
            lit+=light.color*pow(saturate(dot(normal,halfv)),lerp(25,85,_AlpineWet))*.10*_AlpineWet*light.shadowAttenuation;
            lit+=_EmissionColor.rgb*_AlpineNight*1.5;
            lit*=1-_AlpineDaylight*.45;
            return half4(MixFog(lit,i.fog),_AlphaClip>.5?tex.a:1);
        }
        half4 Shadow(V i):SV_Target
        {
            UNITY_SETUP_INSTANCE_ID(i);
            if(_AlphaClip>.5)clip(SAMPLE_TEXTURE2D(_BaseMap,sampler_BaseMap,i.uv).a-_Cutoff);
            return 0;
        }
        ENDHLSL
        Pass
        {
            Name "Forward" Tags {"LightMode"="UniversalForward"}
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma multi_compile_instancing
            #pragma multi_compile_fog
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile_fragment _ _SHADOWS_SOFT
            ENDHLSL
        }
        Pass
        {
            Name "ShadowCaster" Tags {"LightMode"="ShadowCaster"}
            ZWrite On ColorMask 0
            HLSLPROGRAM
            #pragma vertex ShadowVert
            #pragma fragment Shadow
            #pragma multi_compile_instancing
            ENDHLSL
        }
        Pass
        {
            Name "DepthOnly" Tags {"LightMode"="DepthOnly"}
            ZWrite On ColorMask 0
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Shadow
            #pragma multi_compile_instancing
            ENDHLSL
        }
    }
}
