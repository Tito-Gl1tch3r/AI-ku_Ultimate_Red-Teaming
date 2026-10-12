package com.finedjentleman.routinetracker.controllers;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.finedjentleman.routinetracker.models.Activity;
import com.finedjentleman.routinetracker.services.ActivityService;

@RestController
@RequestMapping("/api/v1")
public class ActivityController {

	@Autowired
	ActivityService activityServiceImpl;
	
	@PostMapping("/users/{userId}/activities")
	public void addActivity(@RequestBody Activity activity, @PathVariable Long userId) {
		activityServiceImpl.addActivity(activity, userId);
	}
	
	@DeleteMapping("/users/{userId}/activities/{activityId}")
	public void deleteActivity(@PathVariable Long userId, @PathVariable Long activityId) {
		activityServiceImpl.deleteActivity(userId, activityId);
	}
	
	@PostMapping("/users/{userId}/activities/{activityId}")
	public void updateActivity(@PathVariable Long userId, @PathVariable Long activityId, @RequestBody Activity activity) {
		activityServiceImpl.updateActivity(userId, activityId, activity);
	}
	
}
