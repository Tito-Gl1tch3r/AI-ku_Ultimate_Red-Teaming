#pragma once

#include "jdbgpipeline.h"
#include "handler.h"
#include <map>
#include <unordered_map>
#include <iostream>
#include <vector>
#include <set>
#include <utility>
#include <optional>
#include <boost/unordered/unordered_flat_map.hpp>
#include <array>


struct RelationshipData {
	static constexpr char SIZE = 7;
	//std::vector<int> referees;
	std::array<int, SIZE> referrers;
	std::array<char, SIZE> referrersType; // jvmtiHeapReferenceKind
	char idx = 0;
	int klassTag = 0;
};

class ObjectHandler : public Handler {
protected:
	static boost::unordered_flat_map<std::string, boost::unordered_flat_map<long, jobject>> instanceMap;

	static boost::unordered_flat_map<std::string, bool> instanceMapInit;

	static boost::unordered_flat_map<std::string, int> instanceMapTag;


	static std::vector<RelationshipData>* heapGraph;

	static std::map<int, std::string> classTagMap;

	bool heapGraphBuilt = false;

public:
	ObjectHandler(ServerCommand c, jvmtiEnv* jvmti, JNIEnv* jni, JdbgPipeline* pipeline) : Handler{ c, jvmti, jni, pipeline } {

	}

protected:

	void populateMap(jclass& klass, char* klassName);

	void buildHeapGraph();

	std::optional<std::pair<jclass, jobject>> getObject(long tag, const char* klass, std::map<std::string, jclass>& klassMap);


};