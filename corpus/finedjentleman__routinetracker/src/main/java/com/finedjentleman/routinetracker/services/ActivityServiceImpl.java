package com.finedjentleman.routinetracker.services;

import java.util.Set;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import com.finedjentleman.routinetracker.models.Activity;
import com.finedjentleman.routinetracker.models.User;
import com.finedjentleman.routinetracker.repositories.ActivityRepository;
import com.finedjentleman.routinetracker.repositories.UserRepository;

@Service
public class ActivityServiceImpl implements ActivityService {

	@Autowired
	ActivityRepository activityRepository;
	
	@Autowired
	UserRepository userRepository;
	
	@Override
	public void addActivity(Activity activity, Long userId) {
		
		User user = userRepository.getOne(userId);
		
		activityRepository.save(activity); //saved the activity
		
		activity.setUser(user); //set the reference to the user
		
		Set<Activity> activities = user.getActivities(); //store the list of activities of user temporarily
		activities.add(activity); // add the new activity to the user
		user.setActivities(activities); // set the new activities of the user
		
		userRepository.save(user); // commit
		
	}
	
	@Override
	public void deleteActivity(Long userId, Long activityId) {
		
		User user = userRepository.getOne(userId);
		
		Set<Activity> activities = user.getActivities(); // temporarily
		
		for(Activity activity: activities) {
			if(activity.getId() == activityId) {
				activities.remove(activity); // remove from User entity
				activityRepository.delete(activity); // remove from activityRepository
				break;
			}
		}
		
		user.setActivities(activities); // set the new activities of the user
		
		userRepository.save(user); // commit
		
	}
	
	@Override
	public void updateActivity(Long userId, Long activityId, Activity activity) {
		
		User user = userRepository.getOne(userId);
		
		Set<Activity> activities = user.getActivities(); // temporarily
		
		// first delete the activity in the user
		
		for(Activity oldActivity: activities) {
			if(oldActivity.getId() == activityId) {
				activities.remove(oldActivity); // remove from User entity
				activityRepository.delete(oldActivity); // remove from activityRepository
				break;
			}
		}
		
		//now add the updated activity to the user
		
		activityRepository.save(activity);
		
		activity.setUser(user); //set the reference to the user
		
		activities.add(activity); // add the new activity to the user
		user.setActivities(activities); // set the new activities of the user
		
		userRepository.save(user); // commit
		
	}
	
}
