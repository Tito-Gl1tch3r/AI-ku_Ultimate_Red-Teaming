

#include "handlergetreferences.h"
#include <optional>
#include <json.hpp>
#include <boost/unordered/unordered_flat_map.hpp>


using json = nlohmann::basic_json<>;


HandlerGetReferences::HandlerGetReferences(jvmtiEnv* jvmti, JNIEnv* jni, JdbgPipeline* pipeline) : ObjectHandler{ GET_REFS, jvmti, jni, pipeline } {

}




struct GraphInfo {
	std::vector<int> adj;
	std::vector<char> relationshipType;
	std::string origin;
	bool isRoot;

	NLOHMANN_DEFINE_TYPE_INTRUSIVE(GraphInfo, adj, relationshipType, origin, isRoot)

};

constexpr int MAX_DEPTH = 12;

bool dfs(int node, boolean isFirst, std::string& originalClass,
	std::vector<RelationshipData>* heapGraph, 
	std::map<int, GraphInfo>& subGraph, 
	std::set<int>& visited, 
	std::map<int, std::string>& classTagMap, int depth) {

	if (node == 0) {
		return false;
	}

	if (visited.find(node) != visited.end()) {
		return subGraph.find(node) != subGraph.end();
	}
	visited.insert(node);


	int classTag = (*heapGraph)[node].klassTag;





	std::string className;
	if (classTagMap.find(classTag) != classTagMap.end()) {
		className = classTagMap[classTag];
	}
	else {
		className = "??";
	}

	
	std::string blacklist[]{
	"java",
	"jdk",
	"sun",
	};

	std::string whitelistOverride[]{
		"java/lang",
		"java/util"
	};
	for (std::string& ignorePath : blacklist) {
		if (className.find(ignorePath) != std::string::npos) {

			for (std::string& whitelist : whitelistOverride) {
				if (className.find(whitelist) != std::string::npos) {
					goto skip;
				}
			}


			return false;
		}
	}

	skip: {}
	

	subGraph[node].origin = std::move(className);


	// is static
	if (node == classTag) {
		subGraph[node].origin += " (Class)";
		return true;
	}

	if (depth >= MAX_DEPTH) {
		return true;	
	}


	for (int i = 0; i < (*heapGraph)[node].referrers.size(); i++) {
		if (dfs((*heapGraph)[node].referrers[i], false, originalClass, heapGraph, subGraph, visited, classTagMap, depth++)) {
			subGraph[node].adj.push_back((*heapGraph)[node].referrers[i]);
			subGraph[node].relationshipType.push_back((*heapGraph)[node].referrersType[i]);
		}
	}
	subGraph[node].origin += " (Object)";

	return true;
}


int HandlerGetReferences::handle(char* data, DWORD length, char* responseBuffer, int& status, std::map<std::string, jclass>& klassMap) {
	long tag = *((long*)data);
	char* klass = (data + 4);

	auto result{ getObject(tag, klass, klassMap) };
	if (!result.has_value()) {
		return 0;
	}

	auto [objClass, obj] = (*result);


	if (!heapGraphBuilt) {
		buildHeapGraph();
	}

	jlong objTag;
	jvmti->GetTag(obj, &objTag);

	if (objTag == 0) {
		msgLog("The object was not present in the heap graph.");
		return 0;
	}

	msgLog("Object tag of object: " + std::to_string(objTag));



	std::map<int, GraphInfo> subGraph;
	std::set<int> visited;


	if (classTagMap.find((*heapGraph)[objTag].klassTag) == classTagMap.end()) {
		msgLog("The objects class was not found in the classTagMap");
		return 0;
	}


	std::string klassName = classTagMap[(*heapGraph)[objTag].klassTag];


	dfs(objTag, true, klassName, heapGraph, subGraph, visited, classTagMap, 0);
	msgLog("Set root");
	subGraph[objTag].isRoot = true;

	
	std::map<std::string, GraphInfo> newGraph;

	for (const auto& entry : subGraph) {
		newGraph.insert({ std::to_string(entry.first), entry.second });
	}


	json response = newGraph;



	std::string dump{ response.dump() };
	std::memcpy((void*)responseBuffer, (void*)dump.c_str(), strlen(dump.c_str()));

	return dump.size();
}