#include "objecthandler.h"
#include <string>
#include <optional>
#include <boost/unordered/unordered_flat_map.hpp>

constexpr int HEAP_TAG = 2147483647;



boost::unordered_flat_map<std::string, boost::unordered_flat_map<long, jobject>> ObjectHandler::instanceMap;
boost::unordered_flat_map<std::string, bool> ObjectHandler::instanceMapInit;
boost::unordered_flat_map<std::string, int> ObjectHandler::instanceMapTag;



std::map<int, std::string> ObjectHandler::classTagMap;

std::vector<RelationshipData>* ObjectHandler::heapGraph;



// based on assumption that iterate in same order, which should be true
jint JNICALL iterateHeap(jlong class_tag, jlong size, jlong* tag_ptr, jint length, void* user_data) {
	std::vector<int>* tags = (std::vector<int>*)user_data;
	tags->emplace_back(*(tag_ptr));
	*tag_ptr = HEAP_TAG;
	return JVMTI_VISIT_OBJECTS;
}

int idx = 0;
int exceeded = 0;

jint JNICALL untag(jlong class_tag, jlong size, jlong* tag_ptr, jint length, void* user_data) {
	std::vector<int>* tags = (std::vector<int>*)user_data;

	if (idx >= tags->size()) {
		exceeded++;
		return JVMTI_VISIT_OBJECTS;
	}

	*tag_ptr = (*tags)[idx];
	idx++;
	return JVMTI_VISIT_OBJECTS;
}


void ObjectHandler::populateMap(jclass& klass, char* klassName) {
	jvmtiHeapCallbacks callbacks;
	memset(&callbacks, 0, sizeof(callbacks));
	callbacks.heap_iteration_callback = &iterateHeap;

	std::vector<int> tagPreservation;
	jvmti->IterateThroughHeap(0, klass, &callbacks, &tagPreservation);
	jlong tag{ HEAP_TAG };

	jint objCount;
	jobject* objPtr;
	jvmti->GetObjectsWithTags(1, &tag, &objCount, &objPtr, NULL);


	boost::unordered_flat_map<long, jobject>& theMap{ instanceMap[klassName] };

	for (int i = 0; i < objCount; i++) {
		jobject obj{ *(objPtr + i) };
		theMap.insert({ ++instanceMapTag[klassName], obj});
	}


	jvmti->Deallocate((unsigned char*)objPtr);

	idx = 0;
	exceeded = 0;
	// untag objects
	callbacks.heap_iteration_callback = &untag;
	jvmti->IterateThroughHeap(0, klass, &callbacks, &tagPreservation);

	if (exceeded > 0) {
		msgLog("Bad: idx exceeded in tag preservation by: " + std::to_string(idx));
	}
}

int objectTags = 1;
int count = 0;
int javaLangClassTag;


std::set<int> test;

jint JNICALL referenceCallback(jvmtiHeapReferenceKind reference_kind,
	const jvmtiHeapReferenceInfo* reference_info,
	jlong class_tag,
	jlong referrer_class_tag,
	jlong size,
	jlong* tag_ptr,
	jlong* referrer_tag_ptr,
	jint length,
	void* user_data) {

	int referrerClassTag;

	if (referrer_class_tag == 0 && referrer_tag_ptr == NULL) {
		// is heap root
		return JVMTI_VISIT_OBJECTS;
	}


	if (*(tag_ptr) == 0) {
		*(tag_ptr) = objectTags++;
	}

	if (*(referrer_tag_ptr) == 0) {
		*(referrer_tag_ptr) = objectTags++;
	}

	if (referrer_class_tag == javaLangClassTag) {
		if (*(referrer_tag_ptr) == 0) {
			MessageBoxA(nullptr, "What shouldn't happen happened", "(1)", MB_ICONERROR);
			return JVMTI_VISIT_OBJECTS;
		}
		referrerClassTag = *(referrer_tag_ptr);

		//if (referrer_class_tag == *(referrer_tag_ptr))
		//	return JVMTI_VISIT_OBJECTS;

	}	else {
		referrerClassTag = referrer_class_tag;
	}

	int refereeClassTag;
	if (class_tag == javaLangClassTag) {
		if (*(tag_ptr) == 0) {
			MessageBoxA(nullptr, "What shouldn't happen happened", "(2)", MB_ICONERROR);
			return JVMTI_VISIT_OBJECTS;
		}

		refereeClassTag = *(tag_ptr);
	}
	else {
		refereeClassTag = class_tag;
	}


	std::vector<RelationshipData>* graph = (std::vector<RelationshipData>*)user_data;

	int referee_tag = *(tag_ptr);
	int referrer_tag = *(referrer_tag_ptr);

	if (referee_tag >= graph->size() || referrer_tag >= graph->size()) {
		MessageBoxA(nullptr, "Insufficient Buffer Size", "JDBG @ referenceCallback", MB_ICONERROR);
		return JVMTI_VISIT_ABORT;
	}

	char& idx{ (*graph)[referee_tag].idx };

	if (idx < RelationshipData::SIZE) {
		(*graph)[referee_tag].referrers[idx] = referrer_tag;
		(*graph)[referee_tag].referrersType[idx] = (char)reference_kind;
		idx++;
	}
	




	//(*graph)[referrer_tag].referees.push_back(referee_tag);


	(*graph)[referrer_tag].klassTag = referrerClassTag;
	(*graph)[referee_tag].klassTag = refereeClassTag;
	count++;

	return JVMTI_VISIT_OBJECTS;
}

int tagClasses(std::map<int, std::string>& reverseMap, jvmtiEnv* jvmti) {


	jint count;
	jclass* classes;

	jvmti->GetLoadedClasses(&count, &classes);
	int classClassTag = -1;
	for (int i = 0; i < count; i++) {
		jclass klass = *(classes + i);
		jvmti->SetTag(klass, objectTags);

		char* sig;
		jvmti->GetClassSignature(klass, &sig, NULL);

		if (std::string{ sig } == "Ljava/lang/Class;") {
			classClassTag = objectTags;
		}

		reverseMap[objectTags] = std::string{ sig };

		objectTags++;
	}

	return classClassTag;
}

void printTags(jvmtiEnv* jvmti) {
	jint count;
	jclass* classes;

	jvmti->GetLoadedClasses(&count, &classes);
	jlong tag;
	for (int i = 0; i < count; i++) {
		jclass klass = *(classes + i);
		jvmti->GetTag(klass, &tag);

		
	}

}

int objectCount = 0;
jint JNICALL countObjects(jlong class_tag, jlong size, jlong* tag_ptr, jint length, void* user_data) {
	objectCount++;
	return JVMTI_VISIT_OBJECTS;
}


void ObjectHandler::buildHeapGraph() {
	jvmtiHeapCallbacks cb;
	memset(&cb, 0, sizeof(cb));
	cb.heap_iteration_callback = &countObjects;
	jvmti->IterateThroughHeap(0, NULL, &cb, NULL);



	msgLog("Heap count: " + std::to_string(objectCount));


	heapGraph = new std::vector<RelationshipData>(objectCount+1);

	int classClassTag = tagClasses(classTagMap, jvmti);
	msgLog("Tag map size: " + std::to_string(classTagMap.size()));

	jvmtiHeapCallbacks callbacks;
	memset(&callbacks, 0, sizeof(callbacks));
	callbacks.heap_reference_callback = &referenceCallback;


	javaLangClassTag = classClassTag;


	jvmti->FollowReferences(0, NULL, NULL, &callbacks, heapGraph);


	msgLog("java/lang/Class tag: " + std::to_string(javaLangClassTag));
	msgLog("Built heap graph with relationships: " + std::to_string(count));
	msgLog("test size: " + std::to_string(test.size()));
	printTags(jvmti);
	heapGraphBuilt = true;
}



std::optional<std::pair<jclass, jobject>> ObjectHandler::getObject(long tag, const char* klass, std::map<std::string, jclass>& klassMap) {

	if (klassMap.find(klass) == klassMap.end()) {
		msgLog("Klass not found");
	}

	jclass klassObj{ klassMap[klass] };

	if (!instanceMap.count(klass)) {
		msgLog("Klass not found in instance map");
		return std::nullopt;
	}

	if (!instanceMap[klass].count(tag)) {
		msgLog("Tag not found. Instance map size: " + std::to_string(instanceMap[klass].size()));
		msgLog("Tag: " + std::to_string(tag));
		return std::nullopt;
	}

	jobject obj{ instanceMap[klass][tag] };

	if (jni->IsSameObject(obj, NULL)) {
		msgLog("Object was garbage collected");
		return std::nullopt;
	}

	return std::pair<jclass, jobject>{ klassObj, obj };
}