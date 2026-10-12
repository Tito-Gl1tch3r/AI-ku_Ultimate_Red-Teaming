package com.smartnsoft.sampleokhttp.bo;

import java.io.Serializable;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonProperty.Access;

/**
 * @author Ludovic Roland
 * @since 2018.03.30
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public final class Post
    implements Serializable
{

  @JsonProperty("userId")
  public int userId;

  @JsonProperty(value = "id", access = Access.WRITE_ONLY)
  public int id;

  @JsonProperty("title")
  public String title;

  @JsonProperty("body")
  public String body;

  @Override
  public String toString()
  {
    return "Post{" +
        "userId=" + userId +
        ", id=" + id +
        ", title='" + title + '\'' +
        ", body='" + body + '\'' +
        '}';
  }
}
