package com.finedjentleman.routinetracker.controllers;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.finedjentleman.routinetracker.models.User;
import com.finedjentleman.routinetracker.services.UserService;

@RestController
@RequestMapping("/api/v1")
public class UserController {

	@Autowired
	UserService userServiceImpl;
	
	@PostMapping("/users")
	public void addUser(@RequestBody User user) {
		userServiceImpl.addUser(user);
	}
	
	@GetMapping("/users/{userId}")
	public User getUser(@PathVariable Long userId) {
		return userServiceImpl.getUser(userId);
	}
	
	@DeleteMapping("/users/{userId}")
	public void deleteUser(@PathVariable Long userId) {
		userServiceImpl.deleteUser(userId);
	}
	
}
